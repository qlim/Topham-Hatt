from hatt import HattModel, DataWrapper, preprocess_data, print_model
from pulp.odict import OrderedDict

class FullProblemData(object):
    LOCOS = ['L'+str(i) for i in range(1, 215)] #214 locos
    TRAINS = ['T'+str(i) for i in range(1, 215)] #214 trains 
    YARDS = ['Y'+str(i) for i in range(1, 74)] #73 yards
    STOP_COST = 250
    TRUCK_CAPACITY = 25000
    TIME_HORIZON_WEEKS = 2 
    LOCO_CAPACITY = 4500
    FUEL_RATE = 3.5
    TRUCK_CONTRACT_COST = 4000
    MAX_STOPS = 2

    def __init__(self):
        from os.path import join
        f = open(join("full_data", "schedule.txt"), "r")
        self.SCHEDULE = []
        for l in f.readlines():
            line = l.strip().split('\t')
            self.SCHEDULE.append((line[0], line[1], int(line[2]),
                                       int(line[3])))
        f.close()
        

        #TODO: INEFFICIENT WAY OF STORING DUE TO COMMUTATIVITY
        f = open(join("full_data", "dist.txt"), "r")
        distdata = []
        for l in f.readlines():
            line = l.strip().split('\t')
            distdata.append((line[0], line[1], int(line[2])))
        f.close()
        
        self.DISTANCES = DataWrapper(distdata)


        f = open(join("full_data", "assign.txt"), "r")
        assigndata = []
        for l in f.readlines():
            line = l.strip().split('\t')
            assigndata.append((line[0], int(line[2]), line[1]))
        f.close()
        
        self.ASSIGNMENTS = DataWrapper(assigndata)

        f = open(join("full_data", "fuelcost.txt"), "r")
        fuelcost = []
        for l in f.readlines():
            line = l.strip().split('\t')
            fuelcost.append((line[0], float(line[1].replace('$', ''))))
        f.close()
        
        self.FUEL_COST = DataWrapper(fuelcost)

        preprocess_data(self)

def main():
    data = FullProblemData()
    print "building model"
    model = HattModel(data, disabled_constraints=('a', 'f'))
    print "solving"
    model.solve()
    print_model(model)

if __name__ == '__main__':
    main()

