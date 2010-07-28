f = open("fuelcost.txt", "r")
fuelcost = []
for l in f.readlines():
    line = l.strip().split('\t')
    fuelcost += [tuple([line[0]] + [float(line[1][1:])])]
f.close()
