(define (domain TSPTW)
    (:requirements :strips :typing :negative-preconditions :fluents)
    (:types
        place - object
        depot - place
        customer - place
    )

    (:predicates
        (loc ?c - place)
        (visited ?c - customer)
    )

    (:functions
        (time)
        (ready-time ?c - customer)
        (due-date ?c - customer)
        (travel-cost ?c1 ?c2 - place)
        (total-cost)
    )

    (:action visit
        :parameters (?from - place ?to - customer)
        :precondition (and
            (loc ?from)
            (not (visited ?to))
            (<= (+ (time) (travel-cost ?from ?to)) (due-date ?to))
            (>= (+ (time) (travel-cost ?from ?to)) (ready-time ?to))
        )
        :effect (and
            (not (loc ?from))
            (loc ?to)
            (visited ?to)
            (increase (time) (travel-cost ?from ?to))
            (increase (total-cost) (travel-cost ?from ?to))
        )
    )

    (:action wait-then-visit
        :parameters (?from - place ?to - customer)
        :precondition (and
            (loc ?from)
            (not (visited ?to))
            (< (+ (time) (travel-cost ?from ?to)) (ready-time ?to))
        )
        :effect (and
            (not (loc ?from))
            (loc ?to)
            (visited ?to)
            (assign (time) (ready-time ?to))
            (increase (total-cost) (travel-cost ?from ?to))
        )
    )

    (:action return-to-depot
        :parameters (?from - customer ?to - depot)
        :precondition (and (loc ?from) (forall
                (?c - customer)
                (visited ?c)))
        :effect (and
            (not (loc ?from))
            (loc ?to)
            (increase (time) (travel-cost ?from ?to))
            (increase (total-cost) (travel-cost ?from ?to))
        )
    )
)