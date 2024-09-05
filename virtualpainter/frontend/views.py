from django.shortcuts import render,redirect
from django.contrib.auth import login,authenticate,logout
from django.contrib.auth.models import User
from django.contrib import messages
import cv2
import mediapipe as mp
import time
import os
import win32com.client
import cv2
import numpy as np
import HandTrackingModule as htm


def home(request):
    return render(request,'index.html')

def register(request):
    if (request.method == "POST"):
        n = request.POST['n']
        e = request.POST['e']
        p = request.POST['p']
        cp = request.POST['cp']
        if p == cp:
            user = User.objects.create_user(username=n, email=e, password=p)
            user.save()
        return redirect('frontend:user_login')
    return render(request, 'register.html')

def user_login(request):
    if request.method == "POST":
        username = request.POST['u']
        password = request.POST['p']

        user = authenticate(username=username, password=password)

        if user:
            if user.is_staff:  # Check if the user is an admin
                login(request, user)
                return redirect('/admin/')   # Redirect to the admin dashboard
            else:
                login(request, user)
                return redirect('frontend:home')  # Redirect to the regular user home page
        else:
            messages.error(request, "Invalid credentials")

    return render(request,'login.html')

def User_logout(request):
    logout(request)
    return home(request)

import cv2
import numpy as np
from django.http import JsonResponse

def detect_shapes(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 50, 150)
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    detected_shapes = []
    for contour in contours:
        # Approximate the contour
        approx = cv2.approxPolyDP(contour, 0.04 * cv2.arcLength(contour, True), True)
        x, y, w, h = cv2.boundingRect(approx)

        # Detect shapes
        if len(approx) == 3:
            shape = "Triangle"
        elif len(approx) == 4:
            aspect_ratio = w / float(h)
            if 0.95 <= aspect_ratio <= 1.05:
                shape = "Square"
            else:
                shape = "Rectangle"
        elif len(approx) == 5:
            shape = "Pentagon"
        elif len(approx) == 6:
            shape = "Hexagon"
        else:
            # Check if contour is a circle
            area = cv2.contourArea(contour)
            perimeter = cv2.arcLength(contour, True)
            circularity = 4 * np.pi * area / (perimeter * perimeter)
            if circularity >= 0.85:
                shape = "Circle"
            else:
                shape = ""

        detected_shapes.append((shape, (x, y, w, h)))

    return detected_shapes

def virtual_painter(request):
    cap = cv2.VideoCapture(0)
    cap.set(3, 1280)
    cap.set(4, 720)

    detector = htm.handDetector(detectionCon=0.8)

    drawingColor = (0, 0, 255)
    imgCanvas = np.zeros((720, 1280, 3), np.uint8)
    overlay = np.ones_like(imgCanvas) * 255  # White canvas for overlay

    eraserSize = 50
    pencilSize = 3  # Fixed pencil-like point size

    xp, yp = 0, 0

    # Stack to store history for undo and redo
    history = []
    redo_stack = []

    shape_detection_active = False  # Shape detection toggle
    clear_canvas = False  # Clear canvas toggle

    while True:
        success, image = cap.read()
        image = cv2.flip(image, 1)

        overlay = np.ones_like(imgCanvas) * 255  # Reset overlay
        cv2.rectangle(overlay, (0, 0), (1280, 110), (0, 0, 0), cv2.FILLED)
        cv2.rectangle(overlay, (10, 10), (230, 50), (0, 0, 255), cv2.FILLED)
        cv2.rectangle(overlay, (250, 10), (470, 50), (0, 255, 0), cv2.FILLED)
        cv2.rectangle(overlay, (490, 10), (710, 50), (255, 0, 255), cv2.FILLED)  # Updated to light blue
        cv2.rectangle(overlay, (730, 10), (950, 50), (0, 255, 255), cv2.FILLED)
        cv2.rectangle(overlay, (970, 10), (1270, 50), (255, 255, 255), cv2.FILLED)
        cv2.rectangle(overlay, (10, 60), (130, 100), (255, 0, 255), cv2.FILLED)
        cv2.rectangle(overlay, (1150, 60), (1270, 100), (255, 255, 0), cv2.FILLED)
        cv2.rectangle(overlay, (160, 60), (280, 100), (0, 0, 255) if shape_detection_active else (0, 255, 0),
                      cv2.FILLED)
        cv2.rectangle(overlay, (290, 60), (410, 100), (0, 0, 0), cv2.FILLED)  # Clear button
        cv2.putText(overlay, 'Eraser', (1070, 40), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 0, 0), 3)
        cv2.putText(overlay, 'Undo', (30, 90), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 0, 0), 3)
        cv2.putText(overlay, 'Redo', (1170, 90), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 0, 0), 3)
        cv2.putText(overlay, 'Shapes', (160, 90), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 3)
        cv2.putText(overlay, 'Clear', (310, 90), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 3)  # Clear button text

        image_with_landmarks = image.copy()
        image_with_landmarks = detector.findHands(image_with_landmarks)
        lmlist = detector.findPosition(image_with_landmarks)
        image = cv2.addWeighted(image, 0.5, overlay, 1, 0)

        current_canvas = imgCanvas.copy()

        x1, y1 = 0, 0

        if len(lmlist) != 0:
            x1, y1 = lmlist[8][1:]  # Finger 1
            x2, y2 = lmlist[12][1:]  # Finger 2

            fingers = detector.fingersUp()

            if fingers[1] and fingers[2]:
                xp, yp = 0, 0

                if y1 < 60:
                    if 10 < x1 < 230:
                        drawingColor = (0, 0, 255)
                    elif 250 < x1 < 470:
                        drawingColor = (0, 255, 0)
                    elif 490 < x1 < 710:
                        drawingColor = (255, 0, 255)
                    elif 730 < x1 < 950:
                        drawingColor = (0, 255, 255)
                    elif 970 < x1 < 1270:
                        drawingColor = (0, 0, 0)
                if 140 < x1 < 260 and 60 < y1 < 100:  # Toggle shape detection
                    shape_detection_active = not shape_detection_active
                if 290 < x1 < 410 and 60 < y1 < 100:  # Clear canvas
                    clear_canvas = True

                cv2.rectangle(image, (x1, y1), (x2, y2), drawingColor, cv2.FILLED)

            if fingers[1] and not fingers[2] and y1 > 110:
                x1 = min(max(x1, 0), 1280)
                y1 = min(max(y1, 110), 720)

                cv2.circle(image, (x1, y1), pencilSize, drawingColor, thickness=-1)

                if xp == 0 and yp == 0:
                    xp, yp = x1, y1

                if drawingColor == (0, 0, 0):
                    cv2.line(image, (xp, yp), (x1, y1), drawingColor, eraserSize)
                    cv2.line(imgCanvas, (xp, yp), (x1, y1), drawingColor, eraserSize)
                else:
                    cv2.line(image, (xp, yp), (x1, y1), drawingColor, pencilSize)
                    cv2.line(imgCanvas, (xp, yp), (x1, y1), drawingColor, pencilSize)

                xp, yp = x1, y1

        if shape_detection_active:
            detected_shapes = detect_shapes(imgCanvas)
            for shape, (x, y, w, h) in detected_shapes:
                cv2.putText(image, shape, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
                cv2.drawContours(image, [np.array([(x, y), (x + w, y), (x + w, y + h), (x, y + h)])], 0, (0, 0, 255), 2)

        if clear_canvas:
            imgCanvas = np.zeros((720, 1280, 3), np.uint8)
            history = []
            redo_stack = []
            clear_canvas = False

        imgGray = cv2.cvtColor(imgCanvas, cv2.COLOR_BGR2GRAY)
        _, imgInv = cv2.threshold(imgGray, 20, 255, cv2.THRESH_BINARY_INV)
        imgInv = cv2.cvtColor(imgInv, cv2.COLOR_GRAY2BGR)

        image = cv2.bitwise_and(image, imgInv)
        image = cv2.bitwise_or(image, imgCanvas)

        cv2.imshow('virtual painter', image)
        if image_with_landmarks is not None:
            cv2.imshow('Hand Landmarks', cv2.resize(image_with_landmarks, (400, 300)))  # Resize to 400x300

        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC key to exit
            break

        elif y1 < 120:
            if 10 < x1 < 130:  # Undo
                if len(history) > 0:
                    redo_stack.append(imgCanvas.copy())
                    imgCanvas = history.pop()
            elif 1150 < x1 < 1270:  # Redo
                if len(redo_stack) > 0:
                    history.append(imgCanvas.copy())
                    imgCanvas = redo_stack.pop()
        else:
            if not np.array_equal(current_canvas, imgCanvas):
                history.append(current_canvas.copy())

    cap.release()
    cv2.destroyAllWindows()

    return render(request,'index.html')


from django.shortcuts import render
from django.http import StreamingHttpResponse
import cv2
import os
import numpy as np
import win32com.client
import pythoncom
from cvzone.HandTrackingModule import HandDetector


# Parameters
width, height = 1280, 720
gestureThreshold = 300
pptFilePath = "C:\\Users\\sujit\\pycharm project\\virtual\\samplepptx.pptx"  # Path to your PowerPoint file

# Function to convert ppt slides to images using win32com

import pythoncom
import win32com.client
import os
from .models import Presentation
from .forms import PresentationForm

from django.conf import settings

# Parameters

# Parameters
width, height = 1280, 720
gestureThreshold = 300

def ppt_to_images(ppt_file_path):
    try:
        pythoncom.CoInitialize()  # Initialize COM library
        ppt = win32com.client.Dispatch("PowerPoint.Application")
        presentation = ppt.Presentations.Open(ppt_file_path, WithWindow=False)
        images = []
        for i, slide in enumerate(presentation.Slides):
            temp_path = os.path.join(os.getcwd(), f"slide_{i + 1}.png")
            slide.Export(temp_path, "PNG", width, height)
            images.append(temp_path)
        presentation.Close()
        ppt.Quit()
        return images
    except Exception as e:
        print(f"Error: {e}")
    finally:
        pythoncom.CoUninitialize()  # Uninitialize COM library

def upload_presentation(request):
    if request.method == 'POST':
        form = PresentationForm(request.POST, request.FILES)
        if form.is_valid():
            presentation = form.save()
            imgList = ppt_to_images(presentation.ppt_file.path)

            cap = cv2.VideoCapture(0)
            cap.set(3, width)
            cap.set(4, height)

            detectorHand = HandDetector(detectionCon=0.8, maxHands=1)
            delay = 30
            buttonPressed = False
            counter = 0
            drawMode = False
            imgNumber = 0
            delayCounter = 0
            annotations = [[]]
            annotationNumber = -1
            annotationStart = False
            hs, ws = int(120 * 1), int(213 * 1)  # width and height of small image

            while True:
                success, img = cap.read()
                img = cv2.flip(img, 1)

                if imgNumber < len(imgList):
                    pathFullImage = imgList[imgNumber]
                    imgCurrent = cv2.imread(pathFullImage)
                    if imgCurrent is None:
                        imgCurrent = np.zeros((height, width, 3), np.uint8)
                else:
                    imgCurrent = np.zeros((height, width, 3), np.uint8)

                hands, img = detectorHand.findHands(img)

                cv2.line(img, (0, gestureThreshold), (width, gestureThreshold), (0, 255, 0), 10)

                if hands and buttonPressed is False:
                    hand = hands[0]
                    cx, cy = hand["center"]
                    lmList = hand["lmList"]
                    fingers = detectorHand.fingersUp(hand)

                    xVal = int(np.interp(lmList[8][0], [width // 2, width], [0, width]))
                    yVal = int(np.interp(lmList[8][1], [150, height - 150], [0, height]))
                    indexFinger = xVal, yVal

                    if cy <= gestureThreshold:
                        if fingers == [1, 0, 0, 0, 0]:
                            print("Left")
                            buttonPressed = True
                            if imgNumber > 0:
                                imgNumber -= 1
                                annotations = [[]]
                                annotationNumber = -1
                                annotationStart = False
                        if fingers == [0, 0, 0, 0, 1]:
                            print("Right")
                            buttonPressed = True
                            if imgNumber < len(imgList) - 1:
                                imgNumber += 1
                                annotations = [[]]
                                annotationNumber = -1
                                annotationStart = False

                    if fingers == [0, 1, 1, 0, 0]:
                        cv2.circle(imgCurrent, indexFinger, 12, (0, 0, 255), cv2.FILLED)

                    if fingers == [0, 1, 0, 0, 0]:
                        if annotationStart is False:
                            annotationStart = True
                            annotationNumber += 1
                            annotations.append([])
                        annotations[annotationNumber].append(indexFinger)
                        cv2.circle(imgCurrent, indexFinger, 12, (0, 0, 255), cv2.FILLED)
                    else:
                        annotationStart = False

                    if fingers == [0, 1, 1, 1, 0]:
                        if annotations:
                            annotations.pop(-1)
                            annotationNumber -= 1
                            buttonPressed = True

                else:
                    annotationStart = False

                if buttonPressed:
                    counter += 1
                    if counter > delay:
                        counter = 0
                        buttonPressed = False

                for i, annotation in enumerate(annotations):
                    for j in range(len(annotation)):
                        if j != 0:
                            cv2.line(imgCurrent, annotation[j - 1], annotation[j], (0, 0, 200), 12)

                imgSmall = cv2.resize(img, (ws, hs))
                h, w, _ = imgCurrent.shape
                imgCurrent[0:hs, w - ws: w] = imgSmall

                cv2.imshow("Slides", imgCurrent)
                cv2.imshow("Image", img)

                key = cv2.waitKey(1)
                if key == ord('q'):
                    break

            cap.release()
            cv2.destroyAllWindows()

            # return redirect('home')  # Redirect to avoid resubmission on refresh
    else:
        form = PresentationForm()

    return render(request, 'first.html', {'form': form})




def first(request):
    return render(request, 'first.html')




