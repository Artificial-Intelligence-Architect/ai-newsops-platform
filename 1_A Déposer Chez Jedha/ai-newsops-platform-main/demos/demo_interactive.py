#!/usr/bin/env python3
"""
AI NewsOps Platform - Interactive Demo
======================================

Testez le modèle avec vos propres headlines et descriptions.

Usage:
    python demo_interactive.py

Exemples:
    "Senate votes on climate bill"
    "New iPhone 16 released today"
    "Paris is the best vacation destination"
"""

import sys
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import warnings
warnings.filterwarnings('ignore')

# Label mapping
LABEL_MAPPING = {
    0: "POLITICS",
    1: "WELLNESS",
    2: "ENTERTAINMENT",
    3: "TRAVEL",
    4: "STYLE",
    5: "PARENTING",
    6: "TECH",
    7: "FOOD",
    8: "SCIENCE",
    9: "BUSINESS",
    10: "SPORTS",
    11: "HOME",
    12: "ARTS"
}

# Colors
class Colors:
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def load_model():
    """Load model once"""
    print(f"\n{Colors.CYAN}Loading model...{Colors.END}")
    tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
    model = AutoModelForSequenceClassification.from_pretrained(
        "distilbert-base-uncased",
        num_labels=len(LABEL_MAPPING),
        ignore_mismatched_sizes=True
    )
    model.eval()
    print(f"{Colors.GREEN}✅ Model ready!{Colors.END}\n")
    return model, tokenizer

def predict_category(text: str, model, tokenizer):
    """Predict category for text"""
    inputs = tokenizer(text, max_length=512, padding=True, truncation=True, return_tensors="pt")
    
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        probs = torch.nn.functional.softmax(logits, dim=-1)
    
    pred_idx = torch.argmax(probs, dim=1).item()
    confidence = probs[0][pred_idx].item()
    
    # Get top 3
    top3_probs, top3_indices = torch.topk(probs[0], k=3)
    
    return {
        "category": LABEL_MAPPING[pred_idx],
        "confidence": confidence,
        "top_3": [
            (LABEL_MAPPING[idx.item()], prob.item())
            for idx, prob in zip(top3_indices, top3_probs)
        ]
    }

def main():
    model, tokenizer = load_model()
    
    print(f"{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}AI NewsOps Platform - Interactive Classification{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")
    
    print(f"{Colors.CYAN}Categories available:{Colors.END}")
    for id, label in LABEL_MAPPING.items():
        print(f"  {id:2d}. {label}")
    
    print(f"\n{Colors.CYAN}Enter your text (press Enter twice to submit):{Colors.END}\n")
    
    counter = 0
    while True:
        try:
            print(f"\n{Colors.BOLD}[Test {counter + 1}]{Colors.END}")
            print(f"{Colors.CYAN}Enter headline (or 'quit' to exit):{Colors.END}")
            
            # Read multiline input
            lines = []
            while True:
                line = input("> ")
                if line.lower() == "quit":
                    return
                if not line:
                    break
                lines.append(line)
            
            if not lines:
                print(f"{Colors.YELLOW}⚠️  Empty input, try again{Colors.END}")
                continue
            
            text = " ".join(lines)
            
            # Predict
            print(f"\n{Colors.CYAN}Processing...{Colors.END}")
            result = predict_category(text, model, tokenizer)
            
            # Display results
            print(f"\n{Colors.BOLD}Results:{Colors.END}")
            print(f"  {Colors.GREEN}Category:{Colors.END} {Colors.BOLD}{result['category']}{Colors.END}")
            print(f"  {Colors.GREEN}Confidence:{Colors.END} {result['confidence']:.2%}")
            
            print(f"\n{Colors.BOLD}Top 3 Predictions:{Colors.END}")
            for rank, (cat, conf) in enumerate(result['top_3'], 1):
                print(f"  {rank}. {cat:<15} {conf:.2%}")
            
            counter += 1
            
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}Goodbye!{Colors.END}\n")
            break
        except Exception as e:
            print(f"{Colors.RED}Error: {e}{Colors.END}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"{Colors.RED}Fatal error: {e}{Colors.END}")
        sys.exit(1)
