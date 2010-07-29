from pulp.odict import OrderedDict
from pulp import LpStatus, LpProblem, LpVariable, value 
from pulp import LpBinary, LpInteger, LpAffineExpression

def print_model(model):
    print "STATUS: ", LpStatus[model.status]
    print "TOTAL COST: ", value(model.total_cost)
    print "FUEL COSTS: ", value(model.fuel_costs)
    print "STOP COSTS: ", value(model.stop_costs)
    print "CONTRACT COSTS: ", value(model.contract_costs)

    for yard in model.d.YARDS:
        print "Yard ", yard, value(model.v_contract[yard])

def preprocess_data(d):
    """
    compute useful odicts from problem data for use in modelling MIP
    """

    ####################
    # Computed Data
    #
    # A note about indexing:
    #   days (d) are 1-based, values indexed over days are stored in OrderedDicts
    #   sequence indexes (s) are 0-based, values indexed over these are stored in
    #   normal Python lists.

    # DAYS = 1-based sequence of days
    d.DAYS = range(1, (7*d.TIME_HORIZON_WEEKS)+1)

    ###################
    # d.TRAIN_YARD_SEQ[t] = sequence of yards visited by train t
    # d.TRAIN_DAY_SEQ[t] = sequence of days for train t, meaning that the sth yard
    # that train t visits is d.TRAIN_YARD_SEQ[t][s] on day d.TRAIN_DAY_SEQ[t][s]
    # Days are 1-based.

    d.TRAIN_YARD_SEQ = OrderedDict()
    d.TRAIN_DAY_SEQ = OrderedDict()
    for train in d.TRAINS:
        d.TRAIN_YARD_SEQ[train] = []
        d.TRAIN_DAY_SEQ[train] = []

    for train, yard, seq, day in d.SCHEDULE:
        # we ignore sequence information in SCHEDULE and assume it's
        # sequentially ordered
        d.TRAIN_YARD_SEQ[train].append(yard)
        d.TRAIN_DAY_SEQ[train].append(day)

    ###################
    # d.LOCO_TRAIN_SEQ[j] = sequence of trains for loco j
    # d.LOCO_TRAIN_DAYS[j] = sequence of days for loco j
    # Combined, this information says that the s'th train that loco j
    # pulls is d.LOCO_TRAIN_SEQ[j][s] and it begins pulling the train on
    # day d.LOCO_TRAIN_DAYS[s]
    d.LOCO_TRAIN_SEQ = OrderedDict()
    d.LOCO_TRAIN_DAYS = OrderedDict()
    for loco in d.LOCOS:
        # assumes ASSIGNMENT has data in order, ignores sequence column
        d.LOCO_TRAIN_SEQ[loco] = d.ASSIGNMENTS[loco].values()
        # big assumption: assumes that locos start pulling a new train every day
        # This is the case for the example and full problems, but might
        # not be for other problems. Should really read this in as part of the input
        # data
        d.LOCO_TRAIN_DAYS[loco] = d.DAYS


    ####################
    # The following two correspond to d.TRAIN_YARD_SEQ and d.TRAIN_DAY_SEQ
    # d.LOCO_YARD_SEQ[j] = sequence of yards visited by loco j
    # d.LOCO_DAY_SEQ[j] = sequence of days for loco j, meaning that the sth yard
    # that train t visits is d.LOCO_YARD_SEQ[j][s] on day d.LOCO_DAY_SEQ[t][s]
    # Days are 1-based.
    #
    # d.LOCO_TRAINS_INDEXES[j] = list of sequence of indexes, each sequence corresponding to
    # a train pulled by loco j, containing the indexes of the yards visited


    d.LOCO_YARD_SEQ = OrderedDict()
    d.LOCO_DAY_SEQ = OrderedDict()
    d.LOCO_TRAINS_INDEXES = OrderedDict()
    for loco in d.LOCOS:
        d.LOCO_YARD_SEQ[loco] = []
        d.LOCO_DAY_SEQ[loco] = []
        d.LOCO_TRAINS_INDEXES[loco] = []

        i = 0
        for train, train_day in zip(d.LOCO_TRAIN_SEQ[loco], d.LOCO_TRAIN_DAYS[loco]):
            # append all yards except for destination (because destination is
            # always the first yard of the next train, and we refuel
            # on the day we leave, not arrive)
            train_indexes = []
            for s in range(len(d.TRAIN_YARD_SEQ[train]) - 1):
                d.LOCO_YARD_SEQ[loco].append(d.TRAIN_YARD_SEQ[train][s])

                # since both train_day and TRAIN_DAY_SEQ are 1-based, need to subtract 1
                yard_day = train_day + d.TRAIN_DAY_SEQ[train][s] - 1
                # also, yard_day may need to wrap around back to 1 
                if yard_day > d.DAYS[-1]:
                    yard_day -= d.DAYS[-1]
                
                d.LOCO_DAY_SEQ[loco].append(yard_day)
                
                train_indexes.append(i)
                i += 1
            d.LOCO_TRAINS_INDEXES[loco].append(train_indexes)

    print [d.TRAIN_DAY_SEQ['T2'][s] for s in range(len(d.TRAIN_YARD_SEQ['T2']) - 1)]
    #print d.LOCO_TRAIN_SEQ['L23']
    #print d.LOCO_YARD_SEQ['L23']
    #print d.LOCO_DAY_SEQ['L23']

    ####################
    # d.LOCO_DISTANCE_PREVIOUS[j][s] = distance between s-1 and sth station of loco j
    d.LOCO_DISTANCE_PREVIOUS = OrderedDict()
    for loco in d.LOCOS:

        # distance for the first yard wraps around
        data = [
            d.DISTANCES[ d.LOCO_YARD_SEQ[loco][-1] ][ d.LOCO_YARD_SEQ[loco][0] ]
        ]

        # remaining yard
        for s in range(1, len(d.LOCO_YARD_SEQ[loco])):
            data.append(
                d.DISTANCES[ d.LOCO_YARD_SEQ[loco][s-1] ][ d.LOCO_YARD_SEQ[loco][s] ]
            )
        d.LOCO_DISTANCE_PREVIOUS[loco] = data


    ####################
    # d.YARD_VISITS[i][d] = a set of (j, s) tuples, meaning that on
    # day d, loco j visits yard i as the s'th station in it sequence

    d.YARD_VISITS = OrderedDict()
    for yard in d.YARDS:
        d.YARD_VISITS[yard] = OrderedDict()
        for day in d.DAYS:
            d.YARD_VISITS[yard][day] = []

    for loco in d.LOCOS:
        print loco
        for s, (yard, day) in enumerate(zip(d.LOCO_YARD_SEQ[loco],
                                            d.LOCO_DAY_SEQ[loco])):
            print s, yard, day ##EDIT
            d.YARD_VISITS[yard][day].append((loco, s))


class HattModel(object):
    def __init__(self, data, disabled_constraints=None):
        self.d = data
        self.disabled_constraints = disabled_constraints or ()

        self.build()

    def build(self):
        self.p = LpProblem()
        self._build_vars()
        self._build_objective()
        self._build_constraints()

    def solve(self, cmd=None):
        if cmd:
            self.status = self.p.solve(cmd)
        else:
            self.status = self.p.solve()

        self.post_solve()

    def post_solve(self):
        d = self.d

        # set self.v_stop values if a & f were omitted
        if ("a" in self.disabled_constraints) and ("f" in
                                                   self.disabled_constraints):
            for loco in d.LOCOS:
                for s, yard in enumerate(d.LOCO_YARD_SEQ[loco]):
                    if self.v_flow[loco][s].varValue > 0:
                        self.v_stop[loco][s].varValue = 1.0
                    else:
                        self.v_stop[loco][s].varValue = 0.0

            # reinstation of stop_costs as a component of objective total_costs
            self.total_cost = self.fuel_costs + self.stop_costs + self.contract_costs

    def _build_vars(self):
        """
        Make variables
        """

        d = self.d

        ####################
        # v_initial[j] = fuel held by loco j at start of planning period
        self.v_initial = OrderedDict()

        for loco in d.LOCOS:
            self.v_initial[loco] = LpVariable("initial_%s" % loco, 0, d.LOCO_CAPACITY)

        ###################
        # v_flow[j][s] = fuel purchased for loco j at sth station in sequence
        self.v_flow = OrderedDict()

        for loco in d.LOCOS:
            self.v_flow[loco] = OrderedDict()
            for s, yard in enumerate(d.LOCO_YARD_SEQ[loco]):
                self.v_flow[loco][s]=LpVariable("flow_%s_%s_%s" % (loco, s, yard),
                                              0, d.LOCO_CAPACITY)

        ###################
        # self.v_stop[j][s] = 1 if loco j stops as sth station in sequence
        self.v_stop = OrderedDict()

        for loco in d.LOCOS:
            self.v_stop[loco] = OrderedDict()
            for s, yard in enumerate(d.LOCO_YARD_SEQ[loco]):
                self.v_stop[loco][s] = LpVariable("stop_%s_%s_%s" % (loco, s, yard),
                                              cat=LpBinary)

        ###################
        # self.v_contract[i] = no. of trucks contracted at yard i
        self.v_contract = OrderedDict()

        for yard in d.YARDS:
            # TODO: explicit UB?
            self.v_contract[yard] = LpVariable('contract_%s' % yard, lowBound=0, 
                                         cat=LpInteger)

    def _build_objective(self):

        d = self.d
        fuel_costs = LpAffineExpression()
        total_fuel = OrderedDict()

        for loco in d.LOCOS:
            total_fuel[loco] = LpAffineExpression()
            for s, yard in enumerate(d.LOCO_YARD_SEQ[loco]):
                total_fuel[loco] += self.v_flow[loco][s]
                fuel_costs += d.FUEL_COST[yard] * self.v_flow[loco][s]

        stop_costs = LpAffineExpression()
        for loco in d.LOCOS:
            for s, yard in enumerate(d.LOCO_YARD_SEQ[loco]):
                stop_costs += d.STOP_COST * self.v_stop[loco][s]

        contract_costs = LpAffineExpression()
        for yard in d.YARDS:
            contract_costs += d.TIME_HORIZON_WEEKS * d.TRUCK_CONTRACT_COST * self.v_contract[yard]

#this exclusion of stop_costs is done to entirely eliminate the variables from the problem passed to the solver
        if ("a" in self.disabled_constraints) and ("f" in
                                                   self.disabled_constraints):
            total_cost = fuel_costs + contract_costs
        else:
            total_cost = fuel_costs + stop_costs + contract_costs

        self.p += total_cost, 'total_cost'
        self.total_cost = total_cost
        self.fuel_costs = fuel_costs
        self.total_fuel = total_fuel
        self.stop_costs = stop_costs
        self.contract_costs = contract_costs

    def _build_constraints(self):
        d = self.d
        p = self.p

        ##################
        # CONSTRAINTS
        #
        # Con.a) link self.v_flow to self.v_stop
        if "a" not in self.disabled_constraints:
            for loco in d.LOCOS:
                for s, yard in enumerate(d.LOCO_YARD_SEQ[loco]):
                    p += (
                        self.v_flow[loco][s] <= d.LOCO_CAPACITY * self.v_stop[loco][s]
                    ), 'a_flow_stop_%s_%s_%s' % (loco, s, yard)

        ##################
        # Con.b) enforce fuel level >= 0 when entering each yard
        # Con.c) enforce tank capacity on fuel level before leaving each yard
        #
        # Expression:
        # fuel_before_departure[j][s] = amount of fuel held by loco j before
        # departing the sth yard in its sequence
        fuel_on_arrival = OrderedDict()
        fuel_on_departure = OrderedDict()

        for loco in d.LOCOS:

            # how this part works: fuel_level is an LpAffineExpression that
            # represent the amount of fuel this loco has. We step through each
            # yard in the sequence, removing consumed fuel (constants) 
            # and adding purchased fuel (self.v_flow variables), whilst creating
            # the b & c constraints

            fuel_level = self.v_initial[loco] # the level before leaving the first yard
            # don't need a c) constraint for the first yard because this is 
            # captured by the upperbound on self.v_initial

            fuel_on_arrival[loco] = []
            fuel_on_departure[loco] = [fuel_level]

            # iterate over remaining yards
            for s in range(1, len(d.LOCO_YARD_SEQ[loco])):
                yard = d.LOCO_YARD_SEQ[loco][s]

                #fuel consumed between the previous yard and this one
                consumed = d.FUEL_RATE * d.LOCO_DISTANCE_PREVIOUS[loco][s]
                fuel_level -= consumed

                fuel_on_arrival[loco].append(fuel_level)

                if "b" not in self.disabled_constraints:
                    # create constraint b)
                    p += (
                        fuel_level >= 0
                    ), 'b_fuel_level_%s_%s_%s' % (loco, s, yard)

                # new fuel level before leaving this yard
                fuel_level += self.v_flow[loco][s]
                fuel_on_departure[loco].append(fuel_level)

                if "c" not in self.disabled_constraints:
                    # create constraint c)
                    p += (
                        fuel_level <= d.LOCO_CAPACITY
                    ), 'c_fuel_level_%s_%s_%s' % (loco, s, yard)

            # one more constraint to do - the fuel level when re-entering the
            # origin yard
            s = 0
            yard = d.LOCO_YARD_SEQ[loco][s]
            fuel_level -= d.FUEL_RATE * d.LOCO_DISTANCE_PREVIOUS[loco][s]
            p += (
                fuel_level >= 0
            ), 'b_fuel_level_%s_%s_%s' % (loco, s, yard)
            fuel_on_arrival[loco].insert(0, fuel_level)

        #################
        # Con.d) continuity condition at origin yard, enforce that the
        # amount of fuel we leave with (self.v_initial) is <= the fuel we start
        # with plus any purchases
        if "d" not in self.disabled_constraints:
            for loco in d.LOCOS:
                p += (
                    fuel_on_arrival[loco][0] + self.v_flow[loco][0] >= fuel_on_departure[loco][0]
                ), 'd_continuity_%s' % loco

        ##################
        # Con.e) enforce locos can only refuel at contracted yards, also
        # enforces capacity each day
        for yard in d.YARDS:
            for day in d.DAYS:
                visitors = d.YARD_VISITS[yard][day]

                # total fuel dispensed at this yard on this day
                fuel_taken = sum(self.v_flow[loco][s] for loco, s in visitors)

                # add constraint
                #TODO can we tighten this?
                if "e" not in self.disabled_constraints:
                    p += (
                        fuel_taken <= d.TRUCK_CAPACITY * self.v_contract[yard]
                    ), 'e_yard_capacity_%s_%s' % (yard, day)

        ##################
        # Con.f) prevent trains from making more than MAX_STOPS
        # (excludes origin)
        if "f" not in self.disabled_constraints:
            for loco in d.LOCOS:
                for tnum, indexes in enumerate(d.LOCO_TRAINS_INDEXES[loco]):
                    non_origin_stops = indexes[1:]

                    p += (
                        sum(self.v_stop[loco][s] for s in non_origin_stops) <= d.MAX_STOPS
                    ), 'f_train_stops_%s_%s' % (loco, tnum)


class DataWrapper(object):    
    def __init__(self, data=None):
        self._odict = OrderedDict()

        if data:
            for d in data:
                self[d[:-1]] = d[-1]

    def __setitem__(self, key, value):
        if not isinstance(key, tuple):
            self._odict[key] = value

        od = self._odict
        for i in key[:-1]:
            if i not in od:
                od[i] = OrderedDict()
            od = od[i]
        od[key[-1]] = value

    def __getitem__(self, key):
        if not isinstance(key, tuple):
            return self._odict[key]

        od = self._odict
        for i in key[:-1]:
            od = od[i]
        return od[key[-1]]

    def __repr__(self):
        return 'DataWrapper(%s)' % repr(self._odict)


