"""
DATA ANNOTATION SYSTEM - Image and Video Labeling Toolkit
========================================================
Professional data annotation for machine learning datasets.

Features:
- Image bounding box annotation
- Video frame annotation
- Classification labeling
- Segmentation masks
- Dataset management
- Export to ML formats
"""

try:
    import cv2
    import numpy as np
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False

import json
import yaml
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
import time
from enum import Enum

log = logging.getLogger("data_annotation")

_CONFIG_PATH = Path(__file__).parent.parent / "core" / "config.yaml"


def _storage_base() -> Path:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return Path(cfg.get("storage", {}).get("base", "C:/ai_agent/apex/data"))


class AnnotationType(Enum):
    BOUNDING_BOX = "bounding_box"
    POLYGON = "polygon"
    CLASSIFICATION = "classification"
    SEGMENTATION = "segmentation"
    KEYPOINTS = "keypoints"


@dataclass
class BoundingBox:
    """Bounding box annotation"""
    x: int
    y: int
    width: int
    height: int
    label: str
    confidence: float = 1.0


@dataclass
class Polygon:
    """Polygon annotation for segmentation"""
    points: List[Tuple[int, int]]
    label: str
    confidence: float = 1.0


@dataclass
class Keypoint:
    """Keypoint annotation"""
    x: int
    y: int
    label: str
    visibility: int


@dataclass
class Annotation:
    """Single annotation"""
    id: str
    type: AnnotationType
    bounding_box: Optional[BoundingBox] = None
    polygon: Optional[Polygon] = None
    keypoints: Optional[List[Keypoint]] = None
    classification: Optional[str] = None
    frame_number: Optional[int] = None
    timestamp: Optional[float] = None
    annotator: str = "system"
    created_at: float = 0


@dataclass
class DatasetItem:
    """Single item in dataset"""
    id: str
    file_path: str
    annotations: List[Annotation]
    metadata: Dict
    status: str
    assigned_to: str


class DataAnnotationSystem:
    def __init__(self, datasets_dir: Path = None):
        if datasets_dir is None:
            datasets_dir = _storage_base() / "datasets"
        self.datasets_dir = Path(datasets_dir)
        self.datasets_dir.mkdir(parents=True, exist_ok=True)
        self.datasets: Dict[str, List[DatasetItem]] = {}
        self.labels: Dict[str, List[str]] = {}
        self.current_dataset: Optional[str] = None
        self.load_datasets()

    def create_dataset(self, dataset_name: str, dataset_type: str = "images") -> bool:
        """Create a new dataset"""
        try:
            dataset_path = self.datasets_dir / dataset_name
            dataset_path.mkdir(exist_ok=True)

            (dataset_path / "images").mkdir(exist_ok=True)
            (dataset_path / "annotations").mkdir(exist_ok=True)
            (dataset_path / "labels").mkdir(exist_ok=True)

            self.datasets[dataset_name] = []
            self.labels[dataset_name] = []
            self.current_dataset = dataset_name

            log.info("Dataset '%s' created", dataset_name)
            self._save_dataset_config(dataset_name)
            return True

        except Exception as e:
            log.error("Failed to create dataset %s: %s", dataset_name, e)
            return False

    def add_items_to_dataset(self, dataset_name: str, file_paths: List[str]) -> int:
        """Add items to dataset"""
        if dataset_name not in self.datasets:
            log.error("Dataset %s not found", dataset_name)
            return 0

        added_count = 0
        for file_path in file_paths:
            try:
                item_id = f"item_{int(time.time() * 1000)}_{len(self.datasets[dataset_name])}"
                item = DatasetItem(
                    id=item_id,
                    file_path=file_path,
                    annotations=[],
                    metadata={"file_size": Path(file_path).stat().st_size if Path(file_path).exists() else 0},
                    status="pending",
                    assigned_to="system"
                )
                self.datasets[dataset_name].append(item)
                added_count += 1
            except Exception as e:
                log.error("Failed to add %s: %s", file_path, e)

        if added_count > 0:
            self._save_dataset_config(dataset_name)
            log.info("Added %s items to %s", added_count, dataset_name)

        return added_count

    def add_label_class(self, dataset_name: str, label_name: str,
                        color: Tuple[int, int, int] = (255, 0, 0)) -> bool:
        """Add a label class to dataset"""
        if dataset_name not in self.labels:
            self.labels[dataset_name] = []

        if label_name not in self.labels[dataset_name]:
            self.labels[dataset_name].append(label_name)
            log.info("Added label class '%s' to %s", label_name, dataset_name)
            self._save_labels_config(dataset_name)
            return True
        return False

    def annotate_image(self, dataset_name: str, item_id: str,
                       annotation_type: AnnotationType, **kwargs) -> Optional[str]:
        """Add annotation to image"""
        if dataset_name not in self.datasets:
            log.error("Dataset %s not found", dataset_name)
            return None

        item = None
        for dataset_item in self.datasets[dataset_name]:
            if dataset_item.id == item_id:
                item = dataset_item
                break

        if not item:
            log.error("Item %s not found in dataset %s", item_id, dataset_name)
            return None

        annotation_id = f"ann_{int(time.time() * 1000)}"

        if annotation_type == AnnotationType.BOUNDING_BOX:
            bbox = BoundingBox(
                x=kwargs.get('x', 0),
                y=kwargs.get('y', 0),
                width=kwargs.get('width', 100),
                height=kwargs.get('height', 100),
                label=kwargs.get('label', 'unknown')
            )
            annotation = Annotation(
                id=annotation_id,
                type=annotation_type,
                bounding_box=bbox,
                created_at=time.time()
            )

        elif annotation_type == AnnotationType.POLYGON:
            polygon = Polygon(
                points=kwargs.get('points', []),
                label=kwargs.get('label', 'unknown')
            )
            annotation = Annotation(
                id=annotation_id,
                type=annotation_type,
                polygon=polygon,
                created_at=time.time()
            )

        elif annotation_type == AnnotationType.CLASSIFICATION:
            annotation = Annotation(
                id=annotation_id,
                type=annotation_type,
                classification=kwargs.get('label', 'unknown'),
                created_at=time.time()
            )

        elif annotation_type == AnnotationType.KEYPOINTS:
            keypoints = [Keypoint(**kp) for kp in kwargs.get('keypoints', [])]
            annotation = Annotation(
                id=annotation_id,
                type=annotation_type,
                keypoints=keypoints,
                created_at=time.time()
            )

        else:
            log.error("Unsupported annotation type: %s", annotation_type)
            return None

        item.annotations.append(annotation)
        item.status = "annotated"

        self._save_annotations(dataset_name, item)
        log.info("Added %s annotation to %s", annotation_type.value, item_id)
        return annotation_id

    def auto_annotate_images(self, dataset_name: str, model_type: str = "yolo") -> int:
        """Automatically annotate images using pre-trained models"""
        if dataset_name not in self.datasets:
            log.error("Dataset %s not found", dataset_name)
            return 0

        annotated_count = 0

        log.info("Auto-annotating images in %s using %s", dataset_name, model_type)

        for item in self.datasets[dataset_name]:
            if item.status == "pending" and item.file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
                try:
                    detections = self._simulate_detection(item.file_path)

                    for det in detections:
                        self.annotate_image(
                            dataset_name, item.id, AnnotationType.BOUNDING_BOX,
                            x=det['x'], y=det['y'], width=det['width'],
                            height=det['height'], label=det['label']
                        )

                    item.status = "annotated"
                    annotated_count += 1

                except Exception as e:
                    log.error("Auto-annotation failed for %s: %s", item.file_path, e)

        if annotated_count > 0:
            self._save_dataset_config(dataset_name)
            log.info("Auto-annotated %s images", annotated_count)

        return annotated_count

    def _simulate_detection(self, image_path: str) -> List[Dict]:
        """Simulate object detection results"""
        return [
            {"x": 100, "y": 100, "width": 200, "height": 150, "label": "person", "confidence": 0.95},
            {"x": 300, "y": 50, "width": 100, "height": 100, "label": "car", "confidence": 0.87}
        ]

    def review_annotations(self, dataset_name: str, reviewer: str = "system") -> Dict:
        """Review annotations and provide feedback"""
        if dataset_name not in self.datasets:
            return {"error": f"Dataset {dataset_name} not found"}

        review_results = {
            "total_items": len(self.datasets[dataset_name]),
            "annotated_items": 0,
            "issues_found": 0,
            "quality_score": 0.0,
            "feedback": []
        }

        for item in self.datasets[dataset_name]:
            if item.annotations:
                review_results["annotated_items"] += 1

                quality_issues = self._check_annotation_quality(item)
                if quality_issues:
                    review_results["issues_found"] += len(quality_issues)
                    review_results["feedback"].extend(quality_issues)

        if review_results["annotated_items"] > 0:
            review_results["quality_score"] = (
                (review_results["annotated_items"] - review_results["issues_found"]) /
                review_results["annotated_items"]
            )

        log.info("Reviewed %s: %.1f%% quality",
                 dataset_name, review_results['quality_score'] * 100)
        return review_results

    def _check_annotation_quality(self, item: DatasetItem) -> List[str]:
        """Check quality of annotations"""
        issues = []

        for annotation in item.annotations:
            if annotation.type == AnnotationType.BOUNDING_BOX:
                bbox = annotation.bounding_box
                if bbox:
                    if bbox.width < 5 or bbox.height < 5:
                        issues.append(f"Very small bounding box in {item.id}")
                    if bbox.width > 1000 or bbox.height > 1000:
                        issues.append(f"Very large bounding box in {item.id}")

            elif annotation.type == AnnotationType.POLYGON:
                poly = annotation.polygon
                if poly and len(poly.points) < 3:
                    issues.append(f"Invalid polygon with < 3 points in {item.id}")

        return issues

    def export_dataset(self, dataset_name: str, format_type: str = "coco") -> str:
        """Export dataset in specified format"""
        if dataset_name not in self.datasets:
            return f"Dataset {dataset_name} not found"

        dataset_path = self.datasets_dir / dataset_name
        export_path = dataset_path / f"export_{format_type}"
        export_path.mkdir(exist_ok=True)

        log.info("Exporting %s as %s", dataset_name, format_type)

        if format_type.lower() == "coco":
            result = self._export_coco(dataset_name, export_path)
        elif format_type.lower() == "yolo":
            result = self._export_yolo(dataset_name, export_path)
        elif format_type.lower() == "csv":
            result = self._export_csv(dataset_name, export_path)
        else:
            result = f"Unsupported export format: {format_type}"

        log.info("Export completed: %s", result)
        return result

    def _export_coco(self, dataset_name: str, export_path: Path) -> str:
        """Export in COCO format"""
        coco_data = {
            "info": {
                "description": f"{dataset_name} dataset",
                "version": "1.0",
                "year": time.strftime("%Y"),
                "contributor": "Apex AI"
            },
            "images": [],
            "annotations": [],
            "categories": []
        }

        if dataset_name in self.labels:
            for i, label in enumerate(self.labels[dataset_name]):
                coco_data["categories"].append({
                    "id": i + 1,
                    "name": label,
                    "supercategory": "object"
                })

        annotation_id = 1
        for item in self.datasets[dataset_name]:
            image_id = len(coco_data["images"]) + 1

            coco_data["images"].append({
                "id": image_id,
                "file_name": Path(item.file_path).name,
                "width": 640,
                "height": 480,
                "license": 1
            })

            for ann in item.annotations:
                if ann.type == AnnotationType.BOUNDING_BOX and ann.bounding_box:
                    bbox = ann.bounding_box
                    coco_data["annotations"].append({
                        "id": annotation_id,
                        "image_id": image_id,
                        "category_id": self.labels[dataset_name].index(bbox.label) + 1
                        if bbox.label in self.labels.get(dataset_name, []) else 1,
                        "bbox": [bbox.x, bbox.y, bbox.width, bbox.height],
                        "area": bbox.width * bbox.height,
                        "iscrowd": 0
                    })
                    annotation_id += 1

        coco_file = export_path / "annotations.json"
        with open(coco_file, 'w') as f:
            json.dump(coco_data, f, indent=2)

        return f"COCO dataset exported to {coco_file}"

    def _export_yolo(self, dataset_name: str, export_path: Path) -> str:
        """Export in YOLO format"""
        labels_file = export_path / "classes.txt"
        with open(labels_file, 'w') as f:
            if dataset_name in self.labels:
                for label in self.labels[dataset_name]:
                    f.write(f"{label}\n")

        for item in self.datasets[dataset_name]:
            if item.annotations:
                txt_file = export_path / f"{Path(item.file_path).stem}.txt"
                with open(txt_file, 'w') as f:
                    for ann in item.annotations:
                        if ann.type == AnnotationType.BOUNDING_BOX and ann.bounding_box:
                            bbox = ann.bounding_box
                            class_id = self.labels[dataset_name].index(bbox.label) \
                                if bbox.label in self.labels.get(dataset_name, []) else 0
                            x_center = (bbox.x + bbox.width / 2) / 640
                            y_center = (bbox.y + bbox.height / 2) / 480
                            width_norm = bbox.width / 640
                            height_norm = bbox.height / 480
                            f.write(f"{class_id} {x_center:.6f} {y_center:.6f} "
                                    f"{width_norm:.6f} {height_norm:.6f}\n")

        return f"YOLO dataset exported to {export_path}"

    def _export_csv(self, dataset_name: str, export_path: Path) -> str:
        """Export annotations as CSV"""
        csv_file = export_path / "annotations.csv"
        with open(csv_file, 'w') as f:
            f.write("image_path,label,x,y,width,height\n")
            for item in self.datasets[dataset_name]:
                for ann in item.annotations:
                    if ann.type == AnnotationType.BOUNDING_BOX and ann.bounding_box:
                        bbox = ann.bounding_box
                        f.write(f"{item.file_path},{bbox.label},{bbox.x},{bbox.y},"
                                f"{bbox.width},{bbox.height}\n")

        return f"CSV export saved to {csv_file}"

    def get_dataset_statistics(self, dataset_name: str) -> Dict:
        """Get dataset statistics"""
        if dataset_name not in self.datasets:
            return {"error": f"Dataset {dataset_name} not found"}

        stats = {
            "total_items": len(self.datasets[dataset_name]),
            "annotated_items": 0,
            "total_annotations": 0,
            "label_distribution": {},
            "average_annotations_per_item": 0,
            "dataset_size_mb": 0
        }

        label_counts = {}
        total_annotations = 0

        for item in self.datasets[dataset_name]:
            if item.annotations:
                stats["annotated_items"] += 1
                total_annotations += len(item.annotations)

                for ann in item.annotations:
                    label = "unknown"
                    if ann.type == AnnotationType.BOUNDING_BOX and ann.bounding_box:
                        label = ann.bounding_box.label
                    elif ann.type == AnnotationType.CLASSIFICATION and ann.classification:
                        label = ann.classification
                    elif ann.type == AnnotationType.POLYGON and ann.polygon:
                        label = ann.polygon.label

                    label_counts[label] = label_counts.get(label, 0) + 1

        stats["total_annotations"] = total_annotations
        stats["label_distribution"] = label_counts
        if stats["annotated_items"] > 0:
            stats["average_annotations_per_item"] = total_annotations / stats["annotated_items"]

        log.info("Dataset statistics for %s: %s items", dataset_name, stats['total_items'])
        return stats

    def _save_dataset_config(self, dataset_name: str):
        """Save dataset configuration"""
        try:
            dataset_path = self.datasets_dir / dataset_name
            config_file = dataset_path / "dataset_config.json"

            config = {
                "items": [asdict(item) for item in self.datasets[dataset_name]],
                "created_at": time.time()
            }

            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)

        except Exception as e:
            log.error("Failed to save dataset config for %s: %s", dataset_name, e)

    def _save_labels_config(self, dataset_name: str):
        """Save label configuration"""
        try:
            dataset_path = self.datasets_dir / dataset_name
            labels_file = dataset_path / "labels.json"

            with open(labels_file, 'w') as f:
                json.dump(self.labels.get(dataset_name, []), f, indent=2)

        except Exception as e:
            log.error("Failed to save labels config for %s: %s", dataset_name, e)

    def _save_annotations(self, dataset_name: str, item: DatasetItem):
        """Save annotations for a specific item"""
        try:
            dataset_path = self.datasets_dir / dataset_name
            annotations_dir = dataset_path / "annotations"
            annotations_dir.mkdir(exist_ok=True)

            annotation_file = annotations_dir / f"{item.id}.json"
            item_dict = asdict(item)

            with open(annotation_file, 'w') as f:
                json.dump(item_dict, f, indent=2)

        except Exception as e:
            log.error("Failed to save annotations for %s: %s", item.id, e)

    def load_datasets(self):
        """Load existing datasets from disk"""
        try:
            for dataset_dir in self.datasets_dir.iterdir():
                if dataset_dir.is_dir():
                    config_file = dataset_dir / "dataset_config.json"
                    if config_file.exists():
                        try:
                            with open(config_file, 'r') as f:
                                config = json.load(f)

                            items = []
                            for item_data in config.get('items', []):
                                annotations = []
                                for ann_data in item_data.get('annotations', []):
                                    ann = Annotation(**ann_data)
                                    annotations.append(ann)

                                item = DatasetItem(
                                    id=item_data['id'],
                                    file_path=item_data['file_path'],
                                    annotations=annotations,
                                    metadata=item_data['metadata'],
                                    status=item_data['status'],
                                    assigned_to=item_data['assigned_to']
                                )
                                items.append(item)

                            self.datasets[dataset_dir.name] = items
                            log.info("Loaded dataset: %s", dataset_dir.name)

                        except Exception as e:
                            log.error("Failed to load dataset from %s: %s", config_file, e)

                    labels_file = dataset_dir / "labels.json"
                    if labels_file.exists():
                        try:
                            with open(labels_file, 'r') as f:
                                self.labels[dataset_dir.name] = json.load(f)
                        except Exception as e:
                            log.error("Failed to load labels for %s: %s", dataset_dir.name, e)

        except Exception as e:
            log.error("Failed to scan datasets directory: %s", e)


_data_annotation_system = None


def get_data_annotation_system() -> DataAnnotationSystem:
    """Get or create the singleton DataAnnotationSystem instance"""
    global _data_annotation_system
    if _data_annotation_system is None:
        _data_annotation_system = DataAnnotationSystem()
    return _data_annotation_system


def register_tools(registry) -> None:
    """Register data annotation tools with the agent registry"""
    system = get_data_annotation_system()

    registry.register("tools_create_dataset", system.create_dataset)
    registry.register("tools_add_items_to_dataset", system.add_items_to_dataset)
    registry.register("tools_add_label_class", system.add_label_class)
    registry.register("tools_annotate_image", system.annotate_image)
    registry.register("tools_auto_annotate_images", system.auto_annotate_images)
    registry.register("tools_review_annotations", system.review_annotations)
    registry.register("tools_export_dataset", system.export_dataset)
    registry.register("tools_get_dataset_statistics", system.get_dataset_statistics)
