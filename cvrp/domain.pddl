(define (domain CVRP)
    (:requirements :strips :typing :fluents :negative-preconditions)
    (:types
        place - object
        depot - place
        customer - place
    )
    (:constants
        d1 - depot
    )

    (:predicates
        (loc ?c - place)
        (visited ?c - customer)
    )

    (:functions
        (total-cost)
        (load)
        (vehicles)
        (max_vehicles)
        (capacity)
        (travel-cost ?c1 ?c2 - place)
        (demand ?c - customer)
    )

    (:action visit
        :parameters (?from - place ?to - customer)
        :precondition (and
            (loc ?from)
            (not (visited ?to))
            (<= (+ (load) (demand ?to)) (capacity))
        )
        :effect (and
            (not (loc ?from))
            (loc ?to)
            (visited ?to)
            (increase (load) (demand ?to))
            (increase (total-cost) (travel-cost ?from ?to))
        )
    )

    (:action visit-via-depot
        :parameters (?from - customer ?to - customer)
        :precondition (and
            (loc ?from)
            (not (visited ?to))
            (<= (+ (vehicles) 1) (max_vehicles))
        )
        :effect (and
            (not (loc ?from))
            (loc ?to)
            (visited ?to)
            (assign (load) (demand ?to))
            (increase (vehicles) 1)
            (increase
                (total-cost)
                (+ (travel-cost ?from d1) (travel-cost d1 ?to)))
        )
    )

    (:action return-to-depot
        :parameters (?from - customer)
        :precondition (and
            (loc ?from)
            (forall
                (?c - customer)
                (visited ?c))
        )
        :effect (and
            (not (loc ?from))
            (loc d1)
            (increase (total-cost) (travel-cost ?from d1))
        )
    )
)