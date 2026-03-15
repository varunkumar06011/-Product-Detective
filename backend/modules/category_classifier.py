"""
Product Detective — Category Classifier & Spec Evaluator
Detects product category from title/specs, then scores specs against
category-specific importance weights aligned with user's purchase intent.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SpecScore:
    attribute: str
    display_name: str
    raw_value: str
    score: float        # 0–100
    weight: float       # importance for this category
    note: str


@dataclass
class CategoryEvaluation:
    detected_category: str
    category_confidence: float
    spec_scores: List[SpecScore]
    overall_spec_score: float          # weighted average 0–100
    strengths: List[str]
    weaknesses: List[str]


# ─── Category detection rules ─────────────────────────────────────────────────

CATEGORY_PATTERNS = {
    "laptop": [
        r"\blaptop\b", r"\bnotebook\b", r"\bchromebook\b",
        r"\bgaming pc\b", r"\bultraboo\w*\b",
    ],
    "phone": [
        r"\bsmartphone\b", r"\bmobile\b", r"galaxy [a-z]\d", r"iphone",
        r"\bphone\b", r"\b5g\b.{0,20}\bphone\b",
    ],
    "tablet": [r"\btablet\b", r"\bipad\b", r"\bfire hd\b"],
    "earbuds": [
        r"\bearbuds?\b", r"\btws\b", r"\bwireless earphone\b",
        r"\bheadphone\b", r"\bairpod\b", r"\bneckband\b",
    ],
    "television": [r"\btv\b", r"\btelevision\b", r"\boled\b", r"\bqled\b"],
    "refrigerator": [r"\bfridge\b", r"\brefrigerator\b", r"\bcooler\b"],
    "washing_machine": [r"\bwashing machine\b", r"\bwasher\b", r"\bdryer\b"],
    "camera": [r"\bcamera\b", r"\bdslr\b", r"\bmirrorless\b", r"\baction cam\b"],
    "smartwatch": [r"\bsmartwatch\b", r"\bwatch\b", r"\bband\b.{0,10}\bfitness\b"],
    "backpack": [
        r"\bbackpack\b", r"\bbags?\b", r"\brucksack\b", r"\bdaypack\b",
    ],
}

# ─── Per-category spec scorers ─────────────────────────────────────────────────

class LaptopSpecScorer:
    """Scores laptop specs relevant to gaming, performance, and daily use."""

    GPU_SCORES = {
        "rtx 4090": 100, "rtx 4080": 95, "rtx 4070": 88, "rtx 4060": 80,
        "rtx 3080": 85, "rtx 3070": 78, "rtx 3060": 70, "rtx 3050": 58,
        "rtx 2060": 55, "gtx 1660": 48, "gtx 1650": 38, "iris xe": 25,
        "radeon rx": 50, "amd radeon": 45, "integrated": 15,
    }

    CPU_SCORES = {
        "i9-13": 100, "i9-12": 95, "i7-13": 88, "i7-12": 82,
        "i5-13": 72, "i5-12": 68, "ryzen 9": 90, "ryzen 7": 80,
        "ryzen 5": 65, "i5-11": 58, "i7-11": 72, "i3": 35, "m3 max": 98,
        "m3 pro": 92, "m3": 85, "m2": 80,
    }

    def score(self, specs: Dict[str, str], purpose: str = "gaming") -> List[SpecScore]:
        scores = []
        specs_lower = {k.lower(): v.lower() for k, v in specs.items()}
        all_values = " ".join(specs.values()).lower()

        # GPU
        gpu_score = self._match_score(all_values, self.GPU_SCORES)
        gpu_weight = 0.30 if purpose == "gaming" else 0.15
        scores.append(SpecScore("gpu", "GPU Performance", self._extract(all_values, "rtx|gtx|radeon|iris"),
                                gpu_score, gpu_weight, self._gpu_note(gpu_score, purpose)))

        # CPU
        cpu_score = self._match_score(all_values, self.CPU_SCORES)
        scores.append(SpecScore("cpu", "CPU Performance", self._extract(all_values, r"i[3579]-\d{4}|ryzen [579]|m[23]"),
                                cpu_score, 0.25, ""))

        # RAM
        ram_score = self._ram_score(all_values)
        scores.append(SpecScore("ram", "RAM", self._extract(all_values, r"\d+\s*gb"),
                                ram_score, 0.15, ""))

        # Storage
        storage_score = self._storage_score(all_values)
        scores.append(SpecScore("storage", "Storage (SSD)", self._extract(all_values, r"\d+\s*(gb|tb)"),
                                storage_score, 0.10, ""))

        # Display
        display_score = self._display_score(all_values)
        scores.append(SpecScore("display", "Display", self._extract(all_values, r"\d+\s*hz|[12][0-9]{3}x[12][0-9]{3}"),
                                display_score, 0.10, ""))

        # Battery
        battery_score = self._battery_score(all_values)
        scores.append(SpecScore("battery", "Battery", self._extract(all_values, r"\d+\s*wh"),
                                battery_score, 0.10, ""))

        return scores

    def _match_score(self, text: str, score_map: Dict[str, int]) -> float:
        best = 20  # default: unknown
        for key, score in score_map.items():
            if key in text:
                best = max(best, score)
        return float(best)

    def _ram_score(self, text: str) -> float:
        match = re.search(r"(\d+)\s*gb\s*(ram|ddr|lpddr)", text)
        if match:
            gb = int(match.group(1))
            if gb >= 32: return 100
            if gb >= 16: return 80
            if gb >= 8: return 55
            return 30
        return 40

    def _storage_score(self, text: str) -> float:
        if "ssd" in text:
            match = re.search(r"(\d+)\s*(gb|tb)\s*(ssd|nvme|m\.2)", text)
            if match:
                val = int(match.group(1))
                unit = match.group(2)
                gb = val * 1000 if unit == "tb" else val
                if gb >= 1000: return 90
                if gb >= 512: return 75
                return 55
            return 65  # SSD but unknown size
        return 35  # HDD

    def _display_score(self, text: str) -> float:
        score = 40
        hz_match = re.search(r"(\d+)\s*hz", text)
        if hz_match:
            hz = int(hz_match.group(1))
            if hz >= 240: score += 40
            elif hz >= 144: score += 30
            elif hz >= 120: score += 20
            elif hz >= 60: score += 10
        if "oled" in text: score += 20
        elif "ips" in text or "amoled" in text: score += 10
        if "1440" in text or "2560" in text or "qhd" in text: score += 10
        return min(100, score)

    def _battery_score(self, text: str) -> float:
        match = re.search(r"(\d+)\s*wh", text)
        if match:
            wh = int(match.group(1))
            if wh >= 80: return 90
            if wh >= 65: return 75
            if wh >= 50: return 55
            return 35
        return 40

    def _extract(self, text: str, pattern: str) -> str:
        match = re.search(pattern, text)
        return match.group(0) if match else "N/A"

    def _gpu_note(self, score: float, purpose: str) -> str:
        if purpose == "gaming" and score < 60:
            return "Insufficient GPU for modern gaming — consider upgrading"
        if score >= 80:
            return "Strong GPU for its class"
        return ""


class PhoneSpecScorer:
    def score(self, specs: Dict[str, str], purpose: str = "daily") -> List[SpecScore]:
        all_values = " ".join(specs.values()).lower()
        return [
            SpecScore("camera", "Main Camera", self._extract(all_values, r"\d+ ?mp"),
                      self._camera_score(all_values), 0.25, ""),
            SpecScore("battery", "Battery", self._extract(all_values, r"\d+ ?mah"),
                      self._battery_score(all_values), 0.20, ""),
            SpecScore("processor", "Processor", self._extract(all_values, r"snapdragon|exynos|dimensity|bionic|helio"),
                      self._cpu_score(all_values), 0.20, ""),
            SpecScore("display", "Display", self._extract(all_values, r"amoled|ips|oled|\d+hz"),
                      self._display_score(all_values), 0.15, ""),
            SpecScore("storage", "Storage", self._extract(all_values, r"\d+ ?gb"),
                      self._storage_score(all_values), 0.10, ""),
            SpecScore("charging", "Charging Speed", self._extract(all_values, r"\d+w"),
                      self._charging_score(all_values), 0.10, ""),
        ]

    def _camera_score(self, t):
        m = re.search(r"(\d+)\s*mp", t)
        if m:
            mp = int(m.group(1))
            return min(100, 40 + mp * 0.8)
        return 40

    def _battery_score(self, t):
        m = re.search(r"(\d+)\s*mah", t)
        if m:
            mah = int(m.group(1))
            if mah >= 5000: return 90
            if mah >= 4500: return 78
            if mah >= 4000: return 65
            return 45
        return 50

    def _cpu_score(self, t):
        scores = {"snapdragon 8 gen 3": 100, "snapdragon 8 gen 2": 92, "snapdragon 8 gen 1": 85,
                  "snapdragon 7": 72, "snapdragon 6": 58, "dimensity 9300": 96,
                  "dimensity 9200": 88, "dimensity 8200": 75, "exynos 2400": 88,
                  "exynos 1380": 68, "bionic a17": 98, "helio g99": 60, "helio g85": 45}
        for k, v in scores.items():
            if k in t:
                return float(v)
        return 50

    def _display_score(self, t):
        score = 40
        if "amoled" in t or "oled" in t: score += 25
        m = re.search(r"(\d+)hz", t)
        if m:
            hz = int(m.group(1))
            if hz >= 144: score += 25
            elif hz >= 120: score += 18
            elif hz >= 90: score += 10
        return min(100, score)

    def _storage_score(self, t):
        m = re.search(r"(\d+)\s*gb", t)
        if m:
            gb = int(m.group(1))
            if gb >= 256: return 90
            if gb >= 128: return 72
            if gb >= 64: return 55
        return 40

    def _charging_score(self, t):
        m = re.search(r"(\d+)\s*w", t)
        if m:
            w = int(m.group(1))
            if w >= 100: return 100
            if w >= 65: return 85
            if w >= 45: return 72
            if w >= 25: return 55
            return 35
        return 40

    def _extract(self, t, pattern):
        m = re.search(pattern, t, re.I)
        return m.group(0) if m else "N/A"


class BackpackSpecScorer:
    def score(self, specs: Dict[str, str], purpose: str = "daily") -> List[SpecScore]:
        all_values = " ".join(specs.values()).lower()
        return [
            SpecScore("capacity", "Capacity", self._extract(all_values, r"\d+\s*l(itre)?"),
                      self._capacity_score(all_values), 0.30, ""),
            SpecScore("material", "Material/Durability", self._extract(all_values, r"polyester|nylon|leather|fabric"),
                      self._material_score(all_values), 0.25, ""),
            SpecScore("protection", "Protection", self._extract(all_values, r"raincover|padded|water resistant"),
                      self._protection_score(all_values), 0.25, ""),
            SpecScore("comfort", "Comfort", self._extract(all_values, r"strap|mesh|breathable"),
                      self._comfort_score(all_values), 0.20, ""),
        ]

    def _capacity_score(self, t):
        m = re.search(r"(\d+)\s*l(itre)?", t)
        if m:
            l_val = int(m.group(1))
            if l_val >= 35: return 95
            if l_val >= 25: return 80
            if l_val >= 15: return 60
            return 40
        return 50

    def _material_score(self, t):
        if "polyester" in t or "nylon" in t: return 85
        if "leather" in t: return 90
        return 50

    def _protection_score(self, t):
        score = 40
        if "raincover" in t: score += 30
        if "padded" in t: score += 20
        if "water resistant" in t or "waterproof" in t: score += 10
        return min(100, score)

    def _comfort_score(self, t):
        score = 40
        if "padded strap" in t: score += 30
        if "breathable" in t: score += 20
        if "mesh" in t: score += 10
        return min(100, score)

    def _extract(self, t, pattern):
        m = re.search(pattern, t, re.I)
        return m.group(0) if m else "N/A"


class CategoryClassifier:
    """
    Detects product category via regex pattern matching on title + specs.
    Returns category key + confidence.
    """

    def classify(self, title: str, specs: Dict[str, str]) -> Tuple[str, float]:
        text = (title + " " + " ".join(specs.values())).lower()

        scores: Dict[str, int] = {}
        for category, patterns in CATEGORY_PATTERNS.items():
            score = sum(
                len(re.findall(p, text, re.I))
                for p in patterns
            )
            if score > 0:
                scores[category] = score

        if not scores:
            return "generic", 0.5

        if "backpack" in scores and "laptop" in scores:
            # If both, and the title has 'backpack' or 'bag', prefer backpack
            if re.search(r"backpack|bag", title, re.I):
                return "backpack", 0.95

        best_cat = max(scores, key=scores.__getitem__)
        total = sum(scores.values())
        confidence = min(0.99, scores[best_cat] / total)

        return best_cat, confidence


class SpecEvaluator:
    """
    Routes to the correct spec scorer based on category.
    Returns a CategoryEvaluation with per-attribute scores.
    """

    SCORERS = {
        "laptop": LaptopSpecScorer(),
        "phone": PhoneSpecScorer(),
        "backpack": BackpackSpecScorer(),
    }

    def evaluate(
        self,
        product_title: str,
        specs: Dict[str, str],
        user_purpose: str = "daily",
    ) -> CategoryEvaluation:
        classifier = CategoryClassifier()
        category, confidence = classifier.classify(product_title, specs)

        scorer = self.SCORERS.get(category)
        if scorer is None:
            return CategoryEvaluation(category, confidence, [], 50.0, [], [])

        spec_scores = scorer.score(specs, user_purpose)
        overall = self._weighted_average(spec_scores)

        strengths = [s.display_name for s in spec_scores if s.score >= 75]
        weaknesses = [s.display_name for s in spec_scores if s.score < 50]

        return CategoryEvaluation(
            detected_category=category,
            category_confidence=confidence,
            spec_scores=spec_scores,
            overall_spec_score=overall,
            strengths=strengths,
            weaknesses=weaknesses,
        )

    @staticmethod
    def _weighted_average(scores: List[SpecScore]) -> float:
        if not scores:
            return 50.0
        total_weight = sum(s.weight for s in scores)
        if total_weight == 0:
            return 50.0
        weighted_sum = sum(s.score * s.weight for s in scores)
        return round(weighted_sum / total_weight, 1)
