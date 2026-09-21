"""
Credit-free local detector for ProPath FC.

Runs the trained YOLOv8n model (propathfc_v4.onnx) directly via
onnxruntime — NO Roboflow, NO credits, fully offline. Matches
the exact preprocessing from the Roboflow inference_config:
  - stretch resize to 640x640 (NOT letterbox)
  - RGB, /255 normalization
  - NMS post-processing
  - classes: 0=ball, 1=goalpost

Drop-in replacement for the inference package's get_model():
returns a small object whose .infer(frame, confidence) gives
predictions with .x .y .width .height .confidence .class_name
(matching how ball_detector / goal_detector consume results).
"""
import os
import numpy as np
import onnxruntime as ort

_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "weights", "propathfc_v4.onnx"
)
_CLASS_NAMES = ["ball", "goalpost"]
_INPUT_SIZE = 640


class _Prediction:
    """Mimics the inference package's prediction object."""
    def __init__(self, x, y, w, h, confidence, class_name):
        self.x = x
        self.y = y
        self.width = w
        self.height = h
        self.confidence = confidence
        self.class_name = class_name


class _Result:
    def __init__(self, predictions):
        self.predictions = predictions


class ONNXDetector:
    """Local YOLOv8 ONNX detector. Mirrors get_model().infer()."""

    def __init__(self, model_path=_MODEL_PATH):
        providers = ["CPUExecutionProvider"]
        # Use CoreML on Mac if available (faster on M-series)
        avail = ort.get_available_providers()
        if "CoreMLExecutionProvider" in avail:
            providers = ["CoreMLExecutionProvider",
                         "CPUExecutionProvider"]
        self.session = ort.InferenceSession(model_path,
                                            providers=providers)
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

    def infer(self, frame, confidence=0.4, iou_threshold=0.5):
        """
        frame: BGR image (as OpenCV reads it).
        Returns [ _Result ] (list to match get_model()[0] usage).
        """
        orig_h, orig_w = frame.shape[:2]

        # ── Preprocess: STRETCH resize to 640x640, BGR->RGB, /255 ──
        import cv2
        img = cv2.resize(frame, (_INPUT_SIZE, _INPUT_SIZE),
                         interpolation=cv2.INTER_LINEAR)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1))          # HWC -> CHW
        img = np.expand_dims(img, axis=0)           # add batch

        # ── Run ──
        outputs = self.session.run([self.output_name],
                                   {self.input_name: img})[0]
        # YOLOv8 output shape: (1, 4+num_classes, num_boxes)
        preds = np.squeeze(outputs, axis=0)         # (4+nc, N)
        preds = preds.transpose(1, 0)               # (N, 4+nc)

        num_classes = len(_CLASS_NAMES)
        boxes = preds[:, :4]                         # cx,cy,w,h (in 640 space)
        scores_all = preds[:, 4:4+num_classes]

        class_ids = np.argmax(scores_all, axis=1)
        confidences = np.max(scores_all, axis=1)

        keep = confidences >= confidence
        boxes = boxes[keep]
        class_ids = class_ids[keep]
        confidences = confidences[keep]

        if len(boxes) == 0:
            return [_Result([])]

        # ── Scale boxes from 640x640 (stretch) back to original ──
        sx = orig_w / _INPUT_SIZE
        sy = orig_h / _INPUT_SIZE

        # boxes are cx,cy,w,h in 640 space
        cx = boxes[:, 0] * sx
        cy = boxes[:, 1] * sy
        bw = boxes[:, 2] * sx
        bh = boxes[:, 3] * sy

        # ── NMS (per the config) ──
        x1 = cx - bw / 2
        y1 = cy - bh / 2
        x2 = cx + bw / 2
        y2 = cy + bh / 2
        nms_boxes = np.stack([x1, y1, x2, y2], axis=1)

        keep_idx = _nms(nms_boxes, confidences, iou_threshold)

        predictions = []
        for i in keep_idx:
            predictions.append(_Prediction(
                x=float(cx[i]), y=float(cy[i]),
                w=float(bw[i]), h=float(bh[i]),
                confidence=float(confidences[i]),
                class_name=_CLASS_NAMES[int(class_ids[i])]
            ))
        return [_Result(predictions)]


def _nms(boxes, scores, iou_threshold):
    """Standard NMS. boxes = [x1,y1,x2,y2]."""
    if len(boxes) == 0:
        return []
    x1, y1, x2, y2 = boxes[:,0], boxes[:,1], boxes[:,2], boxes[:,3]
    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]
    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        w = np.maximum(0, xx2 - xx1)
        h = np.maximum(0, yy2 - yy1)
        inter = w * h
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-9)
        order = order[1:][iou < iou_threshold]
    return keep


def get_local_model(model_path=_MODEL_PATH):
    """Drop-in replacement for get_model() — returns ONNXDetector."""
    return ONNXDetector(model_path)
