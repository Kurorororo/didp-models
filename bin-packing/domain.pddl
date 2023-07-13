(define (domain BPP)
    (:requirements :strips :typing :fluents :negative-preconditions)
    (:types
        item
    )
    (:predicates
        (packed ?i - item)
    )
    (:functions
        (capacity)
        (residual)
        (weight ?i - item)
        (total-cost)
    )
    (:action pack
        :parameters (?i - item)
        :precondition (and (not (packed ?i)) (<= (weight ?i) (residual)))
        :effect (and (packed ?i) (decrease (residual) (weight ?i)) (increase (total-cost) 0))
    )
    (:action open-new-bin-and-pack
        :parameters (?i - item)
        :precondition (and (not (packed ?i)) (> (weight ?i) (residual)))
        :effect (and (packed ?i) (assign (residual) (- (capacity) (weight ?i))) (increase (total-cost) 1))
    )
)