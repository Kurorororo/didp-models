import math


def read_optw(filename):
    with open(filename) as f:
        lines = f.readlines()

    values = [v for v in lines[0].rstrip().split()]
    n = int(values[2])

    vertices = []
    x = []
    y = []
    service_time = []
    profit = []
    opening = []
    closing = []

    for i in range(n + 1):
        values = [v for v in lines[2 + i].rstrip().split()]

        assert i == int(values[0])

        vertices.append(i)
        x.append(float(values[1]))
        y.append(float(values[2]))
        service_time.append(float(values[3]))
        profit.append(int(float(values[4])))
        opening.append(float(values[-2]))
        closing.append(float(values[-1]))

    distance = [[None for _ in vertices] for _ in vertices]

    for i in vertices:
        distance[i][i] = 0.0

        for j in vertices:
            if i < j:
                d = math.sqrt((x[i] - x[j]) ** 2 + (y[i] - y[j]) ** 2)
                distance[i][j] = d
                distance[j][i] = d

    return vertices, service_time, profit, opening, closing, distance


def round_to_first(service_time, opening, closing, distance):
    service_time = [int(math.trunc(10 * s)) for s in service_time]
    opening = [int(math.trunc(10 * o)) for o in opening]
    closing = [int(math.trunc(10 * c)) for c in closing]
    distance = [[int(math.trunc(10 * d)) for d in row] for row in distance]

    return service_time, opening, closing, distance


def round_to_second(service_time, opening, closing, distance):
    service_time = [int(math.trunc(100 * s)) for s in service_time]
    opening = [int(math.trunc(100 * o)) for o in opening]
    closing = [int(math.trunc(100 * c)) for c in closing]
    distance = [[int(math.trunc(100 * d)) for d in row] for row in distance]

    return service_time, opening, closing, distance


def validate_optw(service_time, profit, opening, closing, distance, solution, cost):
    t = 0
    reward = 0
    previous = None

    for i in solution:
        if i < 0 or i >= len(service_time):
            print("Node {} does not exist.".format(i))
            return False

        if previous is not None:
            t += distance[previous][i]

        if t < opening[i]:
            t = opening[i]

        if t > closing[i]:
            print(
                "The time {} exceeds the closing time {} at node {}.".format(
                    t, closing[i], i
                )
            )
            return False

        reward += profit[i]
        t += service_time[i]
        previous = i

    if solution[-1] != 0:
        print(
            "The tour does not return to the depot but ends at node {}.".format(
                solution[-1]
            )
        )
        return False

    return True
