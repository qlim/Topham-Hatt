from rasfunctions import *

problemname = "full" # "exercise or "full"

problemdata = loadProblem(problemname)
computeddata = computeVariables(problemdata)

LOCOS, TRAINS, YARDS, SCHEDULE, DISTANCES, ASSIGNMENTS, FUEL_COST, STOP_COST, TRUCK_CAPACITY, TIME_HORIZON_WEEKS, LOCO_CAPACITY, FUEL_RATE, TRUCK_CONTRACT_COST, MAX_STOPS = problemdata
DAYS, TRAIN_YARD_SEQ, TRAIN_DAY_SEQ, LOCO_TRAIN_SEQ, LOCO_YARD_SEQ, LOCO_DAY_SEQ, LOCO_TRAINS_INDEXES, LOCO_DISTANCE_PREVIOUS, YARD_VISITS = computeddata

omissions = ["a","f"]
####################
# Variables
# vInitial[j] = fuel held by loco j at start of planning period
vInitial = OrderedDict()

for loco in LOCOS:
    vInitial[loco] = LpVariable("initial_%s" % loco, 0, LOCO_CAPACITY)

###################
# vFlow[j][s] = fuel purchased for loco j at sth station in sequence
vFlow = OrderedDict()

for loco in LOCOS:
    vFlow[loco] = OrderedDict()
    for s, yard in enumerate(LOCO_YARD_SEQ[loco]):
        vFlow[loco][s]=LpVariable("flow_%s_%s_%s" % (loco, s, yard),
                                      0, LOCO_CAPACITY)

###################
# vStop[j][s] = 1 if loco j stops as sth station in sequence
vStop = OrderedDict()

for loco in LOCOS:
    vStop[loco] = OrderedDict()
    for s, yard in enumerate(LOCO_YARD_SEQ[loco]):
        vStop[loco][s] = LpVariable("stop_%s_%s_%s" % (loco, s, yard),
                                      cat=LpBinary)

###################
# vContract[i] = no. of trucks contracted at yard i
vContract = OrderedDict()

for yard in YARDS:
    # TODO: explicit UB?
    vContract[yard] = LpVariable('contract_%s' % yard, lowBound=0, 
                                 cat=LpInteger)

p = LpProblem()

#################
# OBJECTIVE

fuel_costs = LpAffineExpression()
total_fuel = OrderedDict()
for loco in LOCOS:
    total_fuel[loco] = LpAffineExpression()
    for s, yard in enumerate(LOCO_YARD_SEQ[loco]):
        total_fuel[loco] += vFlow[loco][s]
        fuel_costs += FUEL_COST[yard] * vFlow[loco][s]

stop_costs = LpAffineExpression()
for loco in LOCOS:
    for s, yard in enumerate(LOCO_YARD_SEQ[loco]):
        stop_costs += STOP_COST * vStop[loco][s]

contract_costs = LpAffineExpression()
for yard in YARDS:
    contract_costs += TIME_HORIZON_WEEKS * TRUCK_CONTRACT_COST * vContract[yard]

#this exclusion of stop_costs is done to entirely eliminate the variables from the problem passed to the solver
if ("a" in omissions) and ("f" in omissions):
    total_cost = fuel_costs + contract_costs
else:
    total_cost = fuel_costs + stop_costs + contract_costs

p += total_cost, 'total_cost'


##################
# CONSTRAINTS
#
# Con.a) link vFlow to vStop
if "a" not in omissions:
    for loco in LOCOS:
        for s, yard in enumerate(LOCO_YARD_SEQ[loco]):
            p += (
                vFlow[loco][s] <= LOCO_CAPACITY * vStop[loco][s]
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

for loco in LOCOS:

    # how this part works: fuel_level is an LpAffineExpression that
    # represent the amount of fuel this loco has. We step through each
    # yard in the sequence, removing consumed fuel (constants) 
    # and adding purchased fuel (vFlow variables), whilst creating
    # the b & c constraints

    fuel_level = vInitial[loco] # the level before leaving the first yard
    # don't need a c) constraint for the first yard because this is 
    # captured by the upperbound on vInitial

    fuel_on_arrival[loco] = []
    fuel_on_departure[loco] = [fuel_level]

    # iterate over remaining yards
    for s in range(1, len(LOCO_YARD_SEQ[loco])):
        yard = LOCO_YARD_SEQ[loco][s]

        #fuel consumed between the previous yard and this one
        consumed = FUEL_RATE * LOCO_DISTANCE_PREVIOUS[loco][s]
        fuel_level -= consumed

        fuel_on_arrival[loco].append(fuel_level)

        if "b" not in omissions:
            # create constraint b)
            p += (
                fuel_level >= 0
            ), 'b_fuel_level_%s_%s_%s' % (loco, s, yard)

        # new fuel level before leaving this yard
        fuel_level += vFlow[loco][s]
        fuel_on_departure[loco].append(fuel_level)

        if "c" not in omissions:
            # create constraint c)
            p += (
                fuel_level <= LOCO_CAPACITY
            ), 'c_fuel_level_%s_%s_%s' % (loco, s, yard)

    # one more constraint to do - the fuel level when re-entering the
    # origin yard
    s = 0
    yard = LOCO_YARD_SEQ[loco][s]
    fuel_level -= FUEL_RATE * LOCO_DISTANCE_PREVIOUS[loco][s]
    p += (
        fuel_level >= 0
    ), 'b_fuel_level_%s_%s_%s' % (loco, s, yard)
    fuel_on_arrival[loco].insert(0, fuel_level)

#################
# Con.d) continuity condition at origin yard, enforce that the
# amount of fuel we leave with (vInitial) is <= the fuel we start
# with plus any purchases
if "d" not in omissions:
    for loco in LOCOS:
        p += (
            fuel_on_arrival[loco][0] + vFlow[loco][0] >= fuel_on_departure[loco][0]
        ), 'd_continuity_%s' % loco

##################
# Con.e) enforce locos can only refuel at contracted yards, also
# enforces capacity each day
for yard in YARDS:
    for day in DAYS:
        visitors = YARD_VISITS[yard][day]

        # total fuel dispensed at this yard on this day
        fuel_taken = sum(vFlow[loco][s] for loco, s in visitors)

        # add constraint
        #TODO can we tighten this?
        if "e" not in omissions:
            p += (
                fuel_taken <= TRUCK_CAPACITY * vContract[yard]
            ), 'e_yard_capacity_%s_%s' % (yard, day)

##################
# Con.f) prevent trains from making more than MAX_STOPS
# (excludes origin)
if "f" not in omissions:
    for loco in LOCOS:
        for tnum, indexes in enumerate(LOCO_TRAINS_INDEXES[loco]):
            non_origin_stops = indexes[1:]

            p += (
                sum(vStop[loco][s] for s in non_origin_stops) <= MAX_STOPS
            ), 'f_train_stops_%s_%s' % (loco, tnum)


print len(p.variables())
print len(p.constraints)

p.writeLP('lp.lp')
a= time.time()
status = p.solve()
print "Solve time: ", time.time() - a

# set vStop values if a & f were omitted
if ("a" in omissions) and ("f" in omissions):
    for loco in LOCOS:
        for s, yard in enumerate(LOCO_YARD_SEQ[loco]):
            if vFlow[loco][s].varValue > 0:
                vStop[loco][s].varValue = 1.0
            else:
                vStop[loco][s].varValue = 0.0

    # reinstation of stop_costs as a component of objective total_costs
    total_cost = fuel_costs + stop_costs + contract_costs

print "STATUS: ", LpStatus[status]
print "TOTAL COST: ", value(total_cost)
print "FUEL COSTS: ", value(fuel_costs)
print "STOP COSTS: ", value(stop_costs)
print "CONTRACT COSTS: ", value(contract_costs)

for yard in YARDS:
    print "Yard ", yard, value(vContract[yard])

of = open('out.csv', 'wb')
out = csv.writer(of)

for loco in LOCOS:
    print "PLAN FOR LOCO ", loco
    print "TOTAL FUEL ", value(total_fuel[loco])
    for s, yard in enumerate(LOCO_YARD_SEQ[loco]):
        day = LOCO_DAY_SEQ[loco][s]
        #print yard, s, LOCO_DAY_SEQ[loco][s], value(vFlow[loco][s]),\
        #    value(fuel_on_arrival[loco][s]),\
        #    value(fuel_on_departure[loco][s])
        out.writerow([value(vFlow[loco][s])])

for loco in LOCOS:
    out.writerow([value(vInitial[loco])])

of.close()
