from hatt import HattModel, DataWrapper, preprocess_data, print_model
from pulp import COIN_CMD
from pulp.odict import OrderedDict


class ExampleProblemData(object):
    LOCOS = ['L1', 'L2']
    TRAINS = ['T1', 'T2']
    YARDS = ['Y1', 'Y2', 'Y3', 'Y4']
    SCHEDULE = [
        ('T1', 'Y1', 1, 1),
        ('T1', 'Y2', 2, 1),
        ('T1', 'Y3', 3, 1),
        ('T1', 'Y4', 4, 1),
        ('T2', 'Y4', 1, 1),
        ('T2', 'Y2', 2, 1),
        ('T2', 'Y1', 3, 1),
    ]


    DISTANCES = DataWrapper([
        ('Y1', 'Y2', 106),
        ('Y2', 'Y3', 146),
        ('Y3', 'Y4', 16),
        ('Y2', 'Y4', 162),
        ('Y2', 'Y1', 106),
        ('Y3', 'Y2', 146),
        ('Y4', 'Y3', 16),
        ('Y4', 'Y2', 162),
    ])

    ASSIGNMENTS = DataWrapper([
        ('L1', 1, 'T1'),
        ('L1', 2, 'T2'),
        ('L1', 3, 'T1'),
        ('L1', 4, 'T2'),
        ('L1', 5, 'T1'),
        ('L1', 6, 'T2'),
        ('L1', 7, 'T1'),
        ('L1', 8, 'T2'),
        ('L1', 9, 'T1'),
        ('L1', 10, 'T2'),
        ('L1', 11, 'T1'),
        ('L1', 12, 'T2'),
        ('L1', 13, 'T1'),
        ('L1', 14, 'T2'),
        ('L2', 1, 'T2'),
        ('L2', 2, 'T1'),
        ('L2', 3, 'T2'),
        ('L2', 4, 'T1'),
        ('L2', 5, 'T2'),
        ('L2', 6, 'T1'),
        ('L2', 7, 'T2'),
        ('L2', 8, 'T1'),
        ('L2', 9, 'T2'),
        ('L2', 10, 'T1'),
        ('L2', 11, 'T2'),
        ('L2', 12, 'T1'),
        ('L2', 13, 'T2'),
        ('L2', 14, 'T1'),
    ])

    FUEL_COST = DataWrapper([
        ('Y1', 3.25),
        ('Y2', 3.05), 
        ('Y3', 3.15), 
        ('Y4', 3.15), 
    ])

    STOP_COST = 250
    TRUCK_CAPACITY = 25000
    TIME_HORIZON_WEEKS = 2 
    LOCO_CAPACITY = 4500
    FUEL_RATE = 3.5
    TRUCK_CONTRACT_COST = 4000
    MAX_STOPS = 2

    def __init__(self):
        preprocess_data(self)


def main():
    data = ExampleProblemData()
    print "Building"
    model = HattModel(data)
    print "Solving"
    model.solve(COIN_CMD())
    print_model(model)

if __name__ == '__main__':
    main()

