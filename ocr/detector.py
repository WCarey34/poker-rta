import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


import cv2
import math
import numpy as np
import argparse
from ultralytics import YOLO

# Import the core modules for card labels and poker hand detection
from core.card_labels import classNames  # List of 52 card class names (index 0-51)
from core.PokerHandDetector import findPokerHand  # Function to evaluate best poker hand from a list of card labels

def draw_annotations(frame, detections, color=(0, 255, 0), thickness=2):
    """
    Draw bounding boxes and labels for detections on the frame.
    `detections` is a list of tuples (x1, y1, x2, y2, class_id, confidence).
    """
    for (x1, y1, x2, y2, cls_id, conf) in detections:
        # Draw rectangle
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
        # Prepare label text with class name and confidence
        label = f"{classNames[cls_id]} {conf*100:.1f}%"
        # Compute text size and position (slightly above top-left corner of box)
        text_size, baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        text_x = x1
        text_y = max(y1 - 10, text_size[1] + 10)  # ensure text is within image
        # Draw filled rectangle behind text for readability
        cv2.rectangle(frame, (text_x, text_y - text_size[1] - 5),
                      (text_x + text_size[0] + 2, text_y + baseline - 5),
                      color, cv2.FILLED)
        # Put text (white color)
        cv2.putText(frame, label, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (255, 255, 255), 2, cv2.LINE_AA)
    return frame

def non_maximum_suppression(detections, iou_threshold=0.5):
    """
    Perform an extra NMS on the list of detections to remove duplicates.
    Each detection: (x1, y1, x2, y2, class_id, confidence).
    Returns filtered detections list.
    """
    if not detections:
        return []
    # Convert to array for easier calculations
    det_array = np.array(detections)
    boxes = det_array[:, 0:4].astype(float)
    confs = det_array[:, 5].astype(float)
    class_ids = det_array[:, 4].astype(int)
    # Compute areas for each box
    areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    order = confs.argsort()[::-1]  # sort by confidence, descending
    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        # Compute IoU of the highest confidence box with the rest
        xx1 = np.maximum(boxes[i, 0], boxes[order[1:], 0])
        yy1 = np.maximum(boxes[i, 1], boxes[order[1:], 1])
        xx2 = np.minimum(boxes[i, 2], boxes[order[1:], 2])
        yy2 = np.minimum(boxes[i, 3], boxes[order[1:], 3])
        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        inter = w * h
        # IoU = inter / (areaA + areaB - inter)
        union = areas[i] + areas[order[1:]] - inter
        iou = inter / (union + 1e-6)
        # Indices of boxes with IoU less than threshold (i.e., keep these for next round)
        inds = np.where(iou <= iou_threshold)[0]
        order = order[inds + 1]
    # Return filtered detections
    filtered = [detections[idx] for idx in keep]
    return filtered

def main():
    parser = argparse.ArgumentParser(description="Playing Card Detector using YOLOv8")
    parser.add_argument('--source', type=str, default='0', help="Input source: file/folder path or camera index (0 for webcam)")
    parser.add_argument('--weights', type=str, default='models/best2.pt', help="Path to YOLOv8 model weights file")
    parser.add_argument('--imgsz', type=int, default=640, help="Inference image size (pixels)")
    parser.add_argument('--conf', type=float, default=0.5, help="Confidence threshold for detections")
    parser.add_argument('--iou', type=float, default=0.5, help="IoU threshold for NMS deduplication")
    parser.add_argument('--tracker', type=str, default='', choices=['', 'bytetrack', 'botsort'],
                        help="Optional tracker: 'bytetrack' or 'botsort' (leave empty for no tracking)")
    parser.add_argument('--save', action='store_true', help="Save output (image with annotations or video file)")
    parser.add_argument('--save_path', type=str, default='output.mp4', help="Path to save the output video or image. For video, specify .mp4 file; for image source, a directory or file path.")
    parser.add_argument('--half', action='store_true', help="Use half precision (FP16) for inference (GPU only)")
    parser.add_argument('--stride', type=int, default=1, help="Frame stride for video processing (skip frames for speed, e.g. 2 means process every 2nd frame)")
    args = parser.parse_args()

    # Load YOLO model
    model = YOLO(args.weights)
    # If using GPU, optionally enable half precision for speed
    if args.half:
        # Only set half if device is CUDA
        model.to('cuda' if model.device.type != 'cpu' else 'cpu')
        if model.device.type != 'cpu':
            model.fuse()  # fuse model layers for faster inference (if not already)
            model.model.half()  # set model to half precision

    # Determine if source is webcam, video file, image, or directory
    source = args.source
    is_webcam = source.isdigit()  # if numeric str, assume webcam index
    is_video = False
    is_image = False
    input_paths = []

    if is_webcam:
        source_index = int(source)
        cap = cv2.VideoCapture(source_index)
        is_video = True
    else:
        # Check if source is a video file by extension
        if source.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
            cap = cv2.VideoCapture(source)
            is_video = True
        else:
            # Otherwise assume image or folder of images
            import os
            if os.path.isdir(source):
                # get list of image files in directory
                exts = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')
                for file in sorted(os.listdir(source)):
                    if file.lower().endswith(exts):
                        input_paths.append(os.path.join(source, file))
            else:
                input_paths.append(source)
            if len(input_paths) > 0:
                is_image = True
            else:
                print(f"Error: No images found at {source}")
                return

    # Video writer setup if saving video
    video_writer = None
    if args.save and is_video:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        # Get video FPS for proper output timing. If not available (webcam), use 20 FPS as default.
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps == 0 or fps is None:
            fps = 20
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        video_writer = cv2.VideoWriter(args.save_path, fourcc, fps, (width, height))

    # Process input frames
    unique_cards = []  # track unique cards detected (for image or current frame in video)
    frame_count = 0
    try:
        if is_video:
            # Loop through video frames
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frame_count += 1
                if args.stride > 1 and frame_count % args.stride != 0:
                    # skip this frame for speed
                    continue

                # Run model inference (with or without tracking)
                if args.tracker:
                    # Use YOLO's tracking mode
                    tracker_cfg = args.tracker + ".yaml"  # e.g. "bytetrack.yaml"
                    results = model.track(frame, conf=args.conf, iou=args.iou, imgsz=args.imgsz,
                                          persist=True, stream=False, tracker=tracker_cfg)
                else:
                    results = model.predict(frame, conf=args.conf, iou=args.iou, imgsz=args.imgsz,
                                             device=0 if model.device.type != 'cpu' else 'cpu',  # ensure using the same device
                                             half=args.half, stream=False)
                # `results` is a list; for a single image frame, results[0] is the detection result
                result = results[0]

                # Parse detections
                detections = []
                for box in result.boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    # Only consider detections above confidence threshold (already handled by model.conf, but double-check)
                    if conf >= args.conf:
                        detections.append((x1, y1, x2, y2, cls_id, conf))
                # Extra deduplication using NMS on detections list
                detections = non_maximum_suppression(detections, iou_threshold=args.iou)

                # Prepare list of card labels detected in this frame (unique)
                current_cards = []
                for (x1, y1, x2, y2, cls_id, conf) in detections:
                    current_cards.append(classNames[cls_id])
                # Remove duplicate card labels (if same card class detected multiple times)
                current_cards = list(set(current_cards))

                # If exactly 5 unique cards detected, evaluate the poker hand
                hand_result = None
                if len(current_cards) == 5:
                    hand_result = findPokerHand(current_cards)  # evaluate poker hand from the 5 cards

                # Draw annotations on frame
                frame = draw_annotations(frame, detections)
                if hand_result:
                    # Display the poker hand result on the frame
                    cv2.putText(frame, f"Hand: {hand_result}", (30, 40), cv2.FONT_HERSHEY_SIMPLEX,
                                1.2, (0, 255, 255), 3, cv2.LINE_AA)

                # Show the frame
                cv2.imshow("Card Detection", frame)
                if args.save and video_writer:
                    video_writer.write(frame)
                # Break on 'q' key press
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        elif is_image:
            # Process each image
            for img_path in input_paths:
                img = cv2.imread(img_path)
                if img is None:
                    continue
                # Run detection (single image, no tracking)
                results = model.predict(img, conf=args.conf, iou=args.iou, imgsz=args.imgsz,
                                         device=0 if model.device.type != 'cpu' else 'cpu',
                                         half=args.half, stream=False)
                result = results[0]
                detections = []
                for box in result.boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    if conf >= args.conf:
                        detections.append((x1, y1, x2, y2, cls_id, conf))
                detections = non_maximum_suppression(detections, iou_threshold=args.iou)
                # List unique cards detected
                detected_cards = list({classNames[d[4]] for d in detections})
                # If 5 unique cards, evaluate hand
                hand_result = None
                if len(detected_cards) == 5:
                    hand_result = findPokerHand(detected_cards)
                # Draw and save/show
                annotated_img = draw_annotations(img, detections)
                if hand_result:
                    cv2.putText(annotated_img, f"Hand: {hand_result}", (30, 40), cv2.FONT_HERSHEY_SIMPLEX,
                                1.2, (0, 255, 255), 3, cv2.LINE_AA)
                if args.save:
                    # Determine save path for image
                    if len(input_paths) == 1 and args.save_path.lower().endswith(('.jpg','.png','.jpeg')):
                        out_path = args.save_path
                    else:
                        # save in same directory with suffix
                        import os
                        base_name = os.path.splitext(os.path.basename(img_path))[0]
                        out_path = os.path.join(args.save_path if os.path.isdir(args.save_path) else os.path.dirname(img_path),
                                                f"{base_name}_detected.jpg")
                    cv2.imwrite(out_path, annotated_img)
                    print(f"Saved annotated image to {out_path}")
                # Display the image in a window
                cv2.imshow("Card Detection", annotated_img)
                cv2.waitKey(0)  # wait for key press for each image
    finally:
        # Release resources
        if is_video:
            cap.release()
        if video_writer:
            video_writer.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
