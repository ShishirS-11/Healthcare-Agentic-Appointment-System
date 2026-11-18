
import re
from typing import Any


# These patterns identify possible emergency warning signs.
# This is a conservative initial screening layer, not a diagnosis.

EMERGENCY_RULES = {
    "possible_heart_attack": [
        r"\bsevere chest pain\b",
        r"\bcrushing chest pain\b",
        r"\bchest pressure\b",
        r"\bchest tightness\b",
        r"\bheart attack\b",
        r"\bchest pain.{0,40}(left arm|jaw|back)\b",
    ],

    "possible_stroke": [
        r"\bface drooping\b",
        r"\bsudden weakness\b",
        r"\bsudden numbness\b",
        r"\bslurred speech\b",
        r"\bcannot speak\b",
        r"\btrouble speaking\b",
        r"\bsudden vision loss\b",
        r"\bpossible stroke\b",
    ],

    "severe_breathing_problem": [
        r"\bcannot breathe\b",
        r"\bcan't breathe\b",
        r"\bsevere shortness of breath\b",
        r"\bstruggling to breathe\b",
        r"\bnot breathing\b",
        r"\bblue lips\b",
    ],

    "loss_of_consciousness": [
        r"\bunconscious\b",
        r"\bpassed out\b",
        r"\bnot waking up\b",
        r"\bunresponsive\b",
    ],

    "severe_bleeding": [
        r"\buncontrolled bleeding\b",
        r"\bsevere bleeding\b",
        r"\bbleeding heavily\b",
        r"\bblood won't stop\b",
    ],

    "seizure": [
        r"\bhaving a seizure\b",
        r"\bseizure lasting\b",
        r"\bcontinuous seizures\b",
        r"\bfirst time seizure\b",
    ],

    "severe_allergic_reaction": [
        r"\banaphylaxis\b",
        r"\bthroat closing\b",
        r"\btongue swelling\b",
        r"\bsevere allergic reaction\b",
    ],

    "possible_overdose": [
        r"\boverdose\b",
        r"\btook too many pills\b",
        r"\bpoisoning\b",
        r"\bswallowed poison\b",
    ],

    "self_harm_emergency": [
        r"\bgoing to kill myself\b",
        r"\bwant to end my life\b",
        r"\bplan to commit suicide\b",
        r"\babout to hurt myself\b",
    ],
}


# Basic negation handling to reduce obvious false positives.
# This is deliberately limited; it cannot reliably understand context.

NEGATION_PATTERN = re.compile(
    r"\b(no|not|never|denies|without|don't have|do not have)\b"
)


def _is_negated(text: str, match_start: int) -> bool:
    """
    Check whether a warning-sign phrase is immediately preceded
    by a simple negation within the previous three words.
    """

    preceding_text = text[:match_start]
    preceding_words = preceding_text.split()[-3:]

    if not preceding_words:
        return False

    preceding_phrase = " ".join(preceding_words)

    return bool(NEGATION_PATTERN.search(preceding_phrase))


def screen_emergency_symptoms(
    patient_message: str,
) -> dict[str, Any]:
    """
    Screen a patient's message for predefined emergency warning signs.

    This function:
    - Does not use an LLM.
    - Does not diagnose a medical condition.
    - Returns possible emergency categories.
    - Recommends immediate emergency assessment when a warning sign
      is detected.

    Important: This is only an initial safety layer.
    """

    if not isinstance(patient_message, str):
        return {
            "success": False,
            "emergency_detected": False,
            "error": "Patient message must be text.",
        }

    message = patient_message.strip().lower()

    if not message:
        return {
            "success": False,
            "emergency_detected": False,
            "error": "Patient message cannot be empty.",
        }

    detected_categories = []

    for category, patterns in EMERGENCY_RULES.items():

        category_detected = False

        for pattern in patterns:

            for match in re.finditer(pattern, message):

                if not _is_negated(message, match.start()):
                    category_detected = True
                    break

            if category_detected:
                break

        if category_detected:
            detected_categories.append(category)

    if detected_categories:
        return {
            "success": True,
            "emergency_detected": True,
            "severity": "emergency_warning",
            "matched_categories": detected_categories,
            "requires_immediate_action": True,
            "message": (
                "Possible emergency warning signs detected. "
                "Stop routine appointment screening. Advise the "
                "patient to contact local emergency services or "
                "go to the nearest emergency department immediately. "
                "Do not delay emergency care for an AI assessment."
            ),
        }

    return {
        "success": True,
        "emergency_detected": False,
        "severity": "no_rule_matched",
        "matched_categories": [],
        "requires_immediate_action": False,
        "message": (
            "No predefined emergency warning signs were detected. "
            "Continue the normal screening workflow, while remaining "
            "alert to new symptoms."
        ),
    }
