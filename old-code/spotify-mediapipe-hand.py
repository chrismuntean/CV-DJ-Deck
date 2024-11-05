import cv2
import mediapipe as mp
import math
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize MediaPipe Hands and Drawing modules
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

# Define min and max distances for "volume" calculation
min_distance = 25
max_distance = 100

# Define threshold distances
index_wrist_threshold = 100  # For detecting if index finger is raised
finger_wrist_threshold_low = 100  # For middle and ring fingers near the wrist
pinky_wrist_threshold_high = 100  # For detecting if pinky is raised

# Variable to store the last "volume" value
last_vol_value = 100

# Initialize variables to store the distances between fingers and wrist
h = 0 # This is set to 0 initially to avoid errors when the hand is not detected

# Initialize Spotify client
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv('SPOTIFY_CLIENT_ID'),
    client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
    redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI'),
    scope="user-modify-playback-state user-read-playback-state"
))

# Start capturing video from the webcam
cap = cv2.VideoCapture(0)

with mp_hands.Hands(
    model_complexity=0,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5) as hands:
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            print("Ignoring empty camera frame.")
            continue

        # Convert the BGR image to RGB
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False

        # Process the image and detect hands
        results = hands.process(image)

        # Draw hand landmarks on the original image
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(
                    image, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                # Get coordinates of wrist and fingertips
                h, w, _ = image.shape
                wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
                wrist_x = int(wrist.x * w)
                wrist_y = int(wrist.y * h)

                def get_finger_tip_coords(finger):
                    tip = hand_landmarks.landmark[finger]
                    return int(tip.x * w), int(tip.y * h)

                index_finger_tip_x, index_finger_tip_y = get_finger_tip_coords(
                    mp_hands.HandLandmark.INDEX_FINGER_TIP)
                middle_finger_tip_x, middle_finger_tip_y = get_finger_tip_coords(
                    mp_hands.HandLandmark.MIDDLE_FINGER_TIP)
                ring_finger_tip_x, ring_finger_tip_y = get_finger_tip_coords(
                    mp_hands.HandLandmark.RING_FINGER_TIP)
                pinky_finger_tip_x, pinky_finger_tip_y = get_finger_tip_coords(
                    mp_hands.HandLandmark.PINKY_TIP)
                thumb_tip_x, thumb_tip_y = get_finger_tip_coords(
                    mp_hands.HandLandmark.THUMB_TIP)

                # Calculate distances from wrist to fingertips
                def calculate_distance(x1, y1, x2, y2):
                    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

                index_wrist_distance = calculate_distance(
                    index_finger_tip_x, index_finger_tip_y, wrist_x, wrist_y)
                middle_wrist_distance = calculate_distance(
                    middle_finger_tip_x, middle_finger_tip_y, wrist_x, wrist_y)
                ring_wrist_distance = calculate_distance(
                    ring_finger_tip_x, ring_finger_tip_y, wrist_x, wrist_y)
                pinky_wrist_distance = calculate_distance(
                    pinky_finger_tip_x, pinky_finger_tip_y, wrist_x, wrist_y)

                # Check if the gesture is active
                if (index_wrist_distance > index_wrist_threshold and
                        middle_wrist_distance < finger_wrist_threshold_low and
                        ring_wrist_distance < finger_wrist_threshold_low and
                        pinky_wrist_distance > pinky_wrist_threshold_high):
                    # Calculate distance between thumb and index fingertips
                    thumb_index_distance = calculate_distance(
                        thumb_tip_x, thumb_tip_y, index_finger_tip_x, index_finger_tip_y)

                    # Normalize the distance to a percentage
                    normalized_value = (
                        thumb_index_distance - min_distance) / (max_distance - min_distance)
                    percentage = max(0, min(normalized_value, 1)) * 100

                    # Round the percentage to the nearest whole number
                    percentage = round(percentage)

                    # Update the last "volume" value
                    last_vol_value = percentage

                    # Draw a red line between thumb and index fingertips
                    cv2.line(image, (thumb_tip_x, thumb_tip_y),
                             (index_finger_tip_x, index_finger_tip_y), (0, 0, 255), 2)

                    # Display the current "volume" value in the top-left corner
                    cv2.putText(image, f'Set volume: {percentage}%',
                                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)

                    # Adjust Spotify volume
                    sp.volume(percentage)

        # Display the last "volume" value in the bottom-left corner
        cv2.putText(image, f'Current volume: {last_vol_value}%',
                    (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)

        # Display the image
        cv2.imshow('MediaPipe Hands', image)

        if cv2.waitKey(5) & 0xFF == 27:
            break

cap.release()
cv2.destroyAllWindows()