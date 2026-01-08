"""Knowledge Graph Embedding using TransE algorithm with semantic enhancements.

TransE: Translating Embeddings for Modeling Multi-relational Data
Models relations as translations in embedding space: h + r ≈ t

Enhanced for Tool4Boxology KG with:
- Semantic relationship weighting
- Entity type-aware initialization
- Relation hierarchy handling
- Component-based clustering
- Early stopping with validation
- Learning rate scheduling
- Selective triple filtering for core relationships
"""

from __future__ import annotations

import pathlib
import re
import random
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict

import numpy as np


# Get the absolute path relative to this file's location
SCRIPT_DIR = pathlib.Path(__file__).parent.resolve()
KG_FILE = SCRIPT_DIR / "dataset" / "Tool4BoxologyKG.nt"
EMBEDDING_DIM = 100  # Optimized for smaller KG
LEARNING_RATE = 0.001  # Reduced for stable convergence
MARGIN = 1.0  # Reduced margin for better convergence
NUM_EPOCHS = 500
BATCH_SIZE = 256  # Larger batches for stable gradients
NEGATIVE_SAMPLES = 5  # Reduced negative samples
PATIENCE = 30  # Early stopping patience
VALIDATION_SPLIT = 0.1
L2_LAMBDA = 0.0001  # L2 regularization
OUTPUT_ENTITY_EMBEDDINGS = SCRIPT_DIR / "entity_embeddings.npy"
OUTPUT_RELATION_EMBEDDINGS = SCRIPT_DIR / "relation_embeddings.npy"
OUTPUT_ENTITY_MAP = SCRIPT_DIR / "entity_map.txt"
OUTPUT_RELATION_MAP = SCRIPT_DIR / "relation_map.txt"
OUTPUT_TRIPLES = SCRIPT_DIR / "triples.txt"

# Only keep structural/semantic predicates (filter out labels and rdf:type)
KEEP_PREDICATES = {
    "http://tool4boxology.org/hasInput",
    "http://tool4boxology.org/hasOutput",
    "http://tool4boxology.org/hasProcess",
    "http://tool4boxology.org/hasPattern",
    "http://tool4boxology.org/inputRoleParticipatesInProcess",
    "http://tool4boxology.org/outputRoleParticipatesInProcess",
}

# Semantic weights for different relation types
RELATION_WEIGHTS = {
    "hasPattern": 2.0,  # Strong semantic relationship
    "hasProcess": 1.8,
    "hasInput": 1.6,
    "hasOutput": 1.6,
    "inputRoleParticipatesInProcess": 1.5,
    "outputRoleParticipatesInProcess": 1.5,
}

# Entity type importance
ENTITY_TYPE_IMPORTANCE = {
    "Boxology": 1.5,
    "DesignPattern": 1.4,
    "Component": 1.3,
    "Unknown": 1.0,
}


def is_literal(obj: str) -> bool:
    """Check if object is a literal value."""
    return obj.startswith('"') and obj.endswith('"')


def parse_nt_line(line: str) -> Tuple[str, str, str] | None:
    """Parse a single N-Triples line into (subject, predicate, object)."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    
    # N-Triples format: <subject> <predicate> <object> .
    pattern = r'<([^>]+)>\s+<([^>]+)>\s+<([^>]+)>|<([^>]+)>\s+<([^>]+)>\s+"([^"]+)"'
    match = re.match(pattern, line)
    
    if match:
        if match.group(1):  # URI-URI-URI triple
            return (match.group(1), match.group(2), match.group(3))
        elif match.group(4):  # URI-URI-Literal triple
            return (match.group(4), match.group(5), f'"{match.group(6)}"')
    
    return None


def extract_label_from_uri(uri: str) -> str:
    """Extract readable label from URI."""
    if "#" in uri:
        return uri.split("#")[-1]
    elif "/" in uri:
        return uri.split("/")[-1]
    return uri


def extract_entity_type(uri: str) -> str:
    """Extract entity type from URI pattern."""
    if "Boxology" in uri:
        return "Boxology"
    elif "DesignPattern" in uri:
        return "DesignPattern"
    elif "Component" in uri:
        return "Component"
    return "Unknown"


def extract_relation_type(predicate: str) -> str:
    """Extract relation type from predicate URI."""
    label = extract_label_from_uri(predicate)
    
    # Check for exact matches first
    for key in RELATION_WEIGHTS.keys():
        if key.lower() in label.lower():
            return key
    
    return "other"


def load_kg_triples(kg_file: pathlib.Path) -> Tuple[
    List[Tuple[str, str, str]], 
    Dict[str, int], 
    Dict[str, int],
    Dict[str, str],
    Dict[str, str]
]:
    """Load KG triples and create entity/relation mappings with type information.
    
    Filters out:
    - rdfs:label predicates
    - Literal objects
    - Predicates not in KEEP_PREDICATES
    """
    if not kg_file.exists():
        raise FileNotFoundError(f"KG file not found at {kg_file}")
    
    triples = []
    entities = set()
    relations = set()
    entity_types = {}
    relation_types = {}
    
    filtered_count = 0
    kept_count = 0
    
    with kg_file.open("r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            triple = parse_nt_line(line)
            if not triple:
                continue
            
            subj, pred, obj = triple
            
            # Filter out rdfs:label
            if pred == "http://www.w3.org/2000/01/rdf-schema#label":
                filtered_count += 1
                continue
            
            # Filter out rdf:type (already captured in entity types)
            if pred == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type":
                filtered_count += 1
                continue
            
            # Filter out literal objects
            if is_literal(obj):
                filtered_count += 1
                continue
            
            # Only keep structural predicates
            if pred not in KEEP_PREDICATES:
                filtered_count += 1
                continue
            
            # Keep this triple
            triples.append((subj, pred, obj))
            entities.add(subj)
            entities.add(obj)
            relations.add(pred)
            kept_count += 1
            
            # Store entity types
            entity_types[subj] = extract_entity_type(subj)
            entity_types[obj] = extract_entity_type(obj)
            
            # Store relation types
            relation_types[pred] = extract_relation_type(pred)
            
            if line_num % 1000 == 0:
                print(f"Processed {line_num} lines... (kept: {kept_count}, filtered: {filtered_count})")
    
    print(f"\nFiltering Summary:")
    print(f"  Total lines processed: {line_num}")
    print(f"  Triples kept: {kept_count}")
    print(f"  Triples filtered: {filtered_count}")
    print(f"  Filter rate: {filtered_count/(kept_count+filtered_count)*100:.1f}%")
    
    # Create index mappings
    entity_to_idx = {entity: idx for idx, entity in enumerate(sorted(entities))}
    relation_to_idx = {relation: idx for idx, relation in enumerate(sorted(relations))}
    
    # Convert triples to indices
    indexed_triples = [
        (entity_to_idx[s], relation_to_idx[p], entity_to_idx[o])
        for s, p, o in triples
    ]
    
    return indexed_triples, entity_to_idx, relation_to_idx, entity_types, relation_types


def split_train_validation(
    triples: List[Tuple[int, int, int]], 
    val_split: float
) -> Tuple[List[Tuple[int, int, int]], List[Tuple[int, int, int]]]:
    """Split triples into training and validation sets."""
    random.shuffle(triples)
    val_size = int(len(triples) * val_split)
    return triples[val_size:], triples[:val_size]


def initialize_embeddings_enhanced(
    num_entities: int, 
    num_relations: int, 
    dim: int,
    entity_to_idx: Dict[str, int],
    relation_to_idx: Dict[str, int],
    entity_types: Dict[str, str],
    relation_types: Dict[str, str]
) -> Tuple[np.ndarray, np.ndarray]:
    """Initialize entity and relation embeddings with Xavier initialization."""
    # Xavier initialization
    entity_bound = np.sqrt(6.0 / (num_entities + dim))
    relation_bound = np.sqrt(6.0 / (num_relations + dim))
    
    entity_embeddings = np.random.uniform(-entity_bound, entity_bound, (num_entities, dim))
    relation_embeddings = np.random.uniform(-relation_bound, relation_bound, (num_relations, dim))
    
    # Apply type-aware scaling to entity embeddings
    idx_to_entity = {idx: entity for entity, idx in entity_to_idx.items()}
    for idx in range(num_entities):
        entity = idx_to_entity[idx]
        entity_type = entity_types.get(entity, "Unknown")
        importance = ENTITY_TYPE_IMPORTANCE.get(entity_type, 1.0)
        entity_embeddings[idx] *= importance
    
    # Apply relation-type scaling
    idx_to_relation = {idx: relation for relation, idx in relation_to_idx.items()}
    for idx in range(num_relations):
        relation = idx_to_relation[idx]
        rel_type = relation_types.get(relation, "other")
        weight = RELATION_WEIGHTS.get(rel_type, 1.0)
        relation_embeddings[idx] *= weight
    
    # Normalize entity embeddings
    entity_embeddings = entity_embeddings / (np.linalg.norm(entity_embeddings, axis=1, keepdims=True) + 1e-10)
    
    return entity_embeddings.astype(np.float32), relation_embeddings.astype(np.float32)


def generate_negative_sample(
    triple: Tuple[int, int, int],
    num_entities: int,
    entity_set: Set[Tuple[int, int, int]],
    max_attempts: int = 100
) -> Tuple[int, int, int]:
    """Generate a negative sample by corrupting head or tail entity."""
    h, r, t = triple
    
    for _ in range(max_attempts):
        # Randomly corrupt head or tail
        if random.random() < 0.5:
            h_neg = random.randint(0, num_entities - 1)
            neg_triple = (h_neg, r, t)
        else:
            t_neg = random.randint(0, num_entities - 1)
            neg_triple = (h, r, t_neg)
        
        if neg_triple not in entity_set:
            return neg_triple
    
    # Fallback: return any corruption
    if random.random() < 0.5:
        return (random.randint(0, num_entities - 1), r, t)
    else:
        return (h, r, random.randint(0, num_entities - 1))


def compute_score(h_emb: np.ndarray, r_emb: np.ndarray, t_emb: np.ndarray, norm: str = 'L2') -> float:
    """Compute TransE score with different norms."""
    diff = h_emb + r_emb - t_emb
    if norm == 'L1':
        return np.sum(np.abs(diff))
    elif norm == 'L2':
        return np.linalg.norm(diff)
    return np.linalg.norm(diff)


def evaluate_model_margin(
    triples: List[Tuple[int, int, int]],
    entity_embeddings: np.ndarray,
    relation_embeddings: np.ndarray,
    relation_importance: Dict[int, float],
    num_entities: int,
    neg_samples: int = 3,
    margin: float = 1.0
) -> float:
    """Evaluate model on validation set using margin-based ranking loss.
    
    This matches the training loss computation for better validation.
    """
    triple_set = set(triples)
    total_loss = 0.0
    count = 0
    
    for h, r, t in triples:
        rel_weight = relation_importance.get(r, 1.0)
        
        # Positive score
        pos_score = compute_score(
            entity_embeddings[h],
            relation_embeddings[r],
            entity_embeddings[t]
        )
        
        # Generate negative samples and compute loss
        for _ in range(neg_samples):
            # Simple corruption (head or tail)
            if random.random() < 0.5:
                h_neg = random.randint(0, num_entities - 1)
                neg_score = compute_score(
                    entity_embeddings[h_neg],
                    relation_embeddings[r],
                    entity_embeddings[t]
                )
            else:
                t_neg = random.randint(0, num_entities - 1)
                neg_score = compute_score(
                    entity_embeddings[h],
                    relation_embeddings[r],
                    entity_embeddings[t_neg]
                )
            
            # Margin-based ranking loss with relation weighting
            loss = max(0.0, margin + pos_score - neg_score) * rel_weight
            total_loss += loss
            count += 1
    
    return total_loss / max(count, 1)


def train_transe_enhanced(
    train_triples: List[Tuple[int, int, int]],
    val_triples: List[Tuple[int, int, int]],
    entity_embeddings: np.ndarray,
    relation_embeddings: np.ndarray,
    relation_types: Dict[str, str],
    relation_to_idx: Dict[str, int],
    num_epochs: int,
    batch_size: int,
    learning_rate: float,
    margin: float,
    neg_samples: int,
    patience: int
) -> Tuple[np.ndarray, np.ndarray]:
    """Train TransE model with advanced techniques."""
    num_entities = entity_embeddings.shape[0]
    triple_set = set(train_triples)
    
    print(f"\nTraining TransE with advanced techniques:")
    print(f"  Max epochs: {num_epochs}")
    print(f"  Batch size: {batch_size}")
    print(f"  Initial learning rate: {learning_rate}")
    print(f"  Margin: {margin}")
    print(f"  Negative samples per positive: {neg_samples}")
    print(f"  Early stopping patience: {patience}")
    print(f"  Training triples: {len(train_triples)}")
    print(f"  Validation triples: {len(val_triples)}\n")
    
    # Pre-compute relation importance scores
    idx_to_relation = {idx: relation for relation, idx in relation_to_idx.items()}
    relation_importance = {}
    for idx in range(len(relation_to_idx)):
        relation = idx_to_relation[idx]
        rel_type = relation_types.get(relation, "other")
        relation_importance[idx] = RELATION_WEIGHTS.get(rel_type, 1.0)
    
    best_val_score = float('inf')
    patience_counter = 0
    best_entity_embeddings = entity_embeddings.copy()
    best_relation_embeddings = relation_embeddings.copy()
    
    # Learning rate scheduler
    initial_lr = learning_rate
    
    for epoch in range(num_epochs):
        # Decay learning rate
        current_lr = initial_lr / (1 + 0.01 * epoch)
        
        total_loss = 0.0
        random.shuffle(train_triples)
        
        # Process in batches
        num_batches = (len(train_triples) + batch_size - 1) // batch_size
        
        for batch_idx, batch_start in enumerate(range(0, len(train_triples), batch_size)):
            batch_triples = train_triples[batch_start:batch_start + batch_size]
            batch_loss = 0.0
            
            for h, r, t in batch_triples:
                rel_weight = relation_importance.get(r, 1.0)
                
                # Positive triple score
                pos_score = compute_score(
                    entity_embeddings[h],
                    relation_embeddings[r],
                    entity_embeddings[t]
                )
                
                # Negative samples
                for _ in range(neg_samples):
                    h_neg, r_neg, t_neg = generate_negative_sample((h, r, t), num_entities, triple_set)
                    
                    neg_score = compute_score(
                        entity_embeddings[h_neg],
                        relation_embeddings[r_neg],
                        entity_embeddings[t_neg]
                    )
                    
                    # Margin-based ranking loss with relation weighting in loss only
                    loss = max(0, margin + pos_score - neg_score) * rel_weight
                    
                    if loss > 0:
                        batch_loss += loss
                        
                        # Use current learning rate (no relation weight multiplication)
                        adaptive_lr = current_lr
                        
                        # Gradient update for positive triple
                        grad = 2 * (entity_embeddings[h] + relation_embeddings[r] - entity_embeddings[t])
                        entity_embeddings[h] -= adaptive_lr * grad
                        relation_embeddings[r] -= adaptive_lr * grad
                        entity_embeddings[t] += adaptive_lr * grad
                        
                        # Gradient update for negative triple
                        grad_neg = 2 * (entity_embeddings[h_neg] + relation_embeddings[r_neg] - entity_embeddings[t_neg])
                        entity_embeddings[h_neg] += adaptive_lr * grad_neg
                        relation_embeddings[r_neg] += adaptive_lr * grad_neg
                        entity_embeddings[t_neg] -= adaptive_lr * grad_neg
                        
                        # L2 regularization
                        entity_embeddings[h] -= adaptive_lr * L2_LAMBDA * entity_embeddings[h]
                        entity_embeddings[t] -= adaptive_lr * L2_LAMBDA * entity_embeddings[t]
                        entity_embeddings[h_neg] -= adaptive_lr * L2_LAMBDA * entity_embeddings[h_neg]
                        entity_embeddings[t_neg] -= adaptive_lr * L2_LAMBDA * entity_embeddings[t_neg]
                        relation_embeddings[r] -= adaptive_lr * L2_LAMBDA * relation_embeddings[r]
                        
                        # Normalize entity embeddings (project to unit sphere)
                        norm_h = np.linalg.norm(entity_embeddings[h])
                        norm_t = np.linalg.norm(entity_embeddings[t])
                        norm_h_neg = np.linalg.norm(entity_embeddings[h_neg])
                        norm_t_neg = np.linalg.norm(entity_embeddings[t_neg])
                        
                        if norm_h > 1:
                            entity_embeddings[h] /= norm_h
                        if norm_t > 1:
                            entity_embeddings[t] /= norm_t
                        if norm_h_neg > 1:
                            entity_embeddings[h_neg] /= norm_h_neg
                        if norm_t_neg > 1:
                            entity_embeddings[t_neg] /= norm_t_neg
            
            total_loss += batch_loss
        
        # Calculate average training loss
        avg_train_loss = total_loss / (len(train_triples) * neg_samples) if len(train_triples) > 0 else 0
        
        # Evaluate on validation set using margin-based loss
        val_score = evaluate_model_margin(
            val_triples, 
            entity_embeddings, 
            relation_embeddings,
            relation_importance, 
            num_entities,
            neg_samples=3,
            margin=margin
        )
        
        # Early stopping check
        if val_score < best_val_score:
            best_val_score = val_score
            best_entity_embeddings = entity_embeddings.copy()
            best_relation_embeddings = relation_embeddings.copy()
            patience_counter = 0
        else:
            patience_counter += 1
        
        # Print progress
        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(f"Epoch {epoch + 1:3d}/{num_epochs} - Train Loss: {avg_train_loss:.4f} - Val Loss: {val_score:.4f} - LR: {current_lr:.6f} - Best Val: {best_val_score:.4f}")
        
        # Early stopping
        if patience_counter >= patience:
            print(f"\nEarly stopping at epoch {epoch + 1}. Best validation loss: {best_val_score:.4f}")
            break
    
    return best_entity_embeddings, best_relation_embeddings


def main() -> None:
    print(f"Loading KG from {KG_FILE}...")
    indexed_triples, entity_to_idx, relation_to_idx, entity_types, relation_types = load_kg_triples(KG_FILE)
    
    num_entities = len(entity_to_idx)
    num_relations = len(relation_to_idx)
    
    print(f"\nKG Statistics (after filtering):")
    print(f"  Triples: {len(indexed_triples)}")
    print(f"  Entities: {num_entities}")
    print(f"  Relations: {num_relations}")
    
    # Analyze entity and relation type distribution
    entity_type_counts = defaultdict(int)
    for entity_type in entity_types.values():
        entity_type_counts[entity_type] += 1
    
    relation_type_counts = defaultdict(int)
    for relation_type in relation_types.values():
        relation_type_counts[relation_type] += 1
    
    print(f"\nEntity Type Distribution:")
    for entity_type, count in sorted(entity_type_counts.items(), key=lambda x: -x[1]):
        importance = ENTITY_TYPE_IMPORTANCE.get(entity_type, 1.0)
        print(f"  {entity_type}: {count} (importance: {importance})")
    
    print(f"\nRelation Type Distribution:")
    for relation_type, count in sorted(relation_type_counts.items(), key=lambda x: -x[1]):
        weight = RELATION_WEIGHTS.get(relation_type, 1.0)
        print(f"  {relation_type}: {count} (weight: {weight})")
    
    # Split into train and validation
    train_triples, val_triples = split_train_validation(indexed_triples, VALIDATION_SPLIT)
    
    print(f"\nInitializing embeddings (dim={EMBEDDING_DIM})...")
    entity_embeddings, relation_embeddings = initialize_embeddings_enhanced(
        num_entities, num_relations, EMBEDDING_DIM,
        entity_to_idx, relation_to_idx,
        entity_types, relation_types
    )
    
    # Train TransE with enhanced features
    entity_embeddings, relation_embeddings = train_transe_enhanced(
        train_triples,
        val_triples,
        entity_embeddings,
        relation_embeddings,
        relation_types,
        relation_to_idx,
        NUM_EPOCHS,
        BATCH_SIZE,
        LEARNING_RATE,
        MARGIN,
        NEGATIVE_SAMPLES,
        PATIENCE
    )
    
    # Save embeddings using np.save (creates proper .npy files)
    print("\nSaving outputs...")
    np.save(OUTPUT_ENTITY_EMBEDDINGS, entity_embeddings)
    np.save(OUTPUT_RELATION_EMBEDDINGS, relation_embeddings)
    
    # Create reverse mappings for saving
    idx_to_entity = {idx: entity for entity, idx in entity_to_idx.items()}
    idx_to_relation = {idx: relation for relation, idx in relation_to_idx.items()}
    
    # Save entity mapping with type information
    with OUTPUT_ENTITY_MAP.open("w", encoding="utf-8") as f:
        f.write("idx\tURI\tlabel\ttype\n")
        for idx in range(num_entities):
            entity = idx_to_entity[idx]
            label = extract_label_from_uri(entity)
            entity_type = entity_types.get(entity, "Unknown")
            f.write(f"{idx}\t{entity}\t{label}\t{entity_type}\n")
    
    # Save relation mapping with type information
    with OUTPUT_RELATION_MAP.open("w", encoding="utf-8") as f:
        f.write("idx\tURI\tlabel\ttype\tweight\n")
        for idx in range(num_relations):
            relation = idx_to_relation[idx]
            label = extract_label_from_uri(relation)
            relation_type = relation_types.get(relation, "other")
            weight = RELATION_WEIGHTS.get(relation_type, 1.0)
            f.write(f"{idx}\t{relation}\t{label}\t{relation_type}\t{weight}\n")
    
    # Save triples with indices
    with OUTPUT_TRIPLES.open("w", encoding="utf-8") as f:
        f.write("head\trelation\ttail\n")
        for h, r, t in indexed_triples:
            f.write(f"{h}\t{r}\t{t}\n")
    
    print(f"\n{'='*70}")
    print(f"Training Complete!")
    print(f"{'='*70}")
    print(f"Entity embeddings: ({num_entities}, {EMBEDDING_DIM})")
    print(f"  -> {OUTPUT_ENTITY_EMBEDDINGS.resolve()}")
    print(f"Relation embeddings: ({num_relations}, {EMBEDDING_DIM})")
    print(f"  -> {OUTPUT_RELATION_EMBEDDINGS.resolve()}")
    print(f"Entity mapping -> {OUTPUT_ENTITY_MAP.resolve()}")
    print(f"Relation mapping -> {OUTPUT_RELATION_MAP.resolve()}")
    print(f"Triples -> {OUTPUT_TRIPLES.resolve()}")
    print(f"\n✓ TransE training with semantic enhancements complete!")


if __name__ == "__main__":
    main()
