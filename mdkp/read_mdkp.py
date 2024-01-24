def read_mdkp(filename):
    with open(filename) as f:
        lines = f.readlines()

    first_line = lines[0].rstrip().split()
    n = int(first_line[0])
    m = int(first_line[1])
    profit = [int(p) for p in lines[1].rstrip().split()]
    weight = []

    for i in range(m):
        weight.append([int(w) for w in lines[2 + i].rstrip().split()])

    capacity = [int(c) for c in lines[2 + m].rstrip().split()]

    return n, m, profit, weight, capacity


def validate_mdkp(m, profit, weight, capacity, solution, cost):
    for i in range(m):
        total_weight = sum(weight[i][j] for j in solution)

        if total_weight > capacity[i]:
            print(
                "Total weight {} exceeds capacity {} for dimension {}.".format(
                    total_weight, capacity[i], i
                )
            )
            return False

    total_profit = sum(profit[j] for j in solution)

    if total_profit != cost:
        print(
            "Total profit {} is different from the solution cost {}.".format(
                total_profit, cost
            )
        )

        return False

    return True
