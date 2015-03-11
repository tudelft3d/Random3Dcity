#!/usr/bin/python
# -*- coding: utf-8 -*-

# The MIT License (MIT)

# This code is part of the Random3Dcity package

# Copyright (c) 2015
# Filip Biljecki
# Delft University of Technology
# fbiljecki@gmail.com

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
Python script to generate ground truth model specifications
"""

import uuid
import random
from lxml import etree
from math import sqrt, trunc, floor
import argparse

def argRead(ar, default=None):
    """Corrects the argument input in case it is not in the format True/False."""
    if ar == "0" or ar == "False":
        ar = False
    elif ar == "1" or ar == "True":
        ar = True
    elif ar is None:
        if default:
            ar = default
        else:
            ar = False
    else:
        raise ValueError("Argument value not recognised.")
    return ar

#-- Parse command-line arguments
PARSER = argparse.ArgumentParser(description='Generator of buildings in own format (original, sizes, roof, ...).')
PARSER.add_argument('-n', '--number',
    help='Number of buildings to generate.', required=False)
PARSER.add_argument('-o', '--filename',
    help='Filename to be written containing the data of the buildings (XML).', required=False)
PARSER.add_argument('-r', '--rotation',
    help='Enable rotation. By default it is False. Allowed options: 0/1 or False/True.', required=False)
PARSER.add_argument('-c', '--crs',
    help='Origin of the reference system (-o Nordoostpolder, default = (0,0,0))', required=False)
PARSER.add_argument('-s', '--street',
    help='Generate a road network.', required=False)
PARSER.add_argument('-v', '--vegetation',
    help='Generate vegetation.', required=False)
PARSER.add_argument('-p', '--parts',
    help='Generate parts of buildings, such as garages.', required=False)
ARGS = vars(PARSER.parse_args())
NUMBEROFBUILDINGS = ARGS['number']
FILENAME = ARGS['filename']
CRS = ARGS['crs']
ROTATIONENABLED = argRead(ARGS['rotation'])
STREETS = argRead(ARGS['street'])
VEGETATION = argRead(ARGS['vegetation'])
BUILDINGPARTS = argRead(ARGS['parts'])

#-- Streets and rotated buildings don't look well together. Same with CRS.
if STREETS and ROTATIONENABLED:
    raise ValueError("I cannot process both rotated buildings and road network. Please disable one of the two.")
elif STREETS and CRS:
    raise ValueError("I cannot process both the non-local CRS and road network. Please disable one of the two.")


#-- Parametres
# Size of the cells of buildings in metres
CELLSIZE = 20.0

def buildinggenerator(n, vegetationcells=False, crs=None):
    """
    Generate n buildings with random properties.
    """

    specifications = etree.Element("specifications")

    rmax = 0
    cmax = 0

    #-- For each building run the randomizer independently
    for i in range(0, n):
        #-- Save the location in the cell for each of the building (for the streets)
        if vegetationcells:
            if i in vegetationcells:
                continue
        cell = buildingParametres(specifications, i, n, crs)
        r = cell[0]
        c = cell[1]
        if r > rmax:
            rmax = r
        if c > cmax:
            cmax = c

    return specifications, [rmax, cmax]


def buildingParametres(specifications, i, n, crs = None):
    """
    Generate the properties of a building in a totally random way.
    """

    #-- The roof types
    rooftypes = ['Flat', 'Shed', 'Hipped', 'Gabled', 'Pyramidal']

    #-- Unique UUID for each building. This will later be translated to gml:id in CityGML
    name = str(uuid.uuid4())

    #-- Element tree, building
    building = etree.SubElement(specifications, "building")
    building.attrib['ID'] = name

    #-- Footprint shape. Only rectangular supported at the moment
    footprintShape = etree.SubElement(building, "footprint")
    footprintShape.text = "Rectangular"

    #-- Origin of each building in the global system
    origin = etree.SubElement(building, "origin")
    o = arranger(i, n, crs)
    origin.text = str(o[0]) + " " + str(o[1]) + " " + str(o[2])

    #-- Order of the building in the grid
    order = o[3]
    orderXML = etree.SubElement(building, "order")
    orderXML.text = str(o[3][0]) + " " + str(o[3][1])

    #-- Angle of building in degrees (2D plane)
    angle = etree.SubElement(building, "rotation")
    if ROTATIONENABLED:
        angle.text = str(round(random.uniform(-45.0, 45.0), 2))
    else:
        angle.text = '0'

    #-- Randomise dimensions of the building body (width, length) in metres
    xs = round(random.uniform(3, 10), 2)
    ys = round(random.uniform(3, 10), 2)
    #-- Randomise the number of storeys and their height
    floors = random.randint(1, 5)
    floorHeight = round(random.uniform(3.0, 3.5), 2)
    #-- The height is derived from the number of storeys and their height
    zs = float(round(floors * floorHeight, 2))

    #-- Their storage in the XML
    xsize = etree.SubElement(building, "xSize")
    xsize.text = str(xs)
    ysize = etree.SubElement(building, "ySize")
    ysize.text = str(ys)
    zsize = etree.SubElement(building, "zSize")
    zsize.text = str(zs)
    floorsXML = etree.SubElement(building, "floors")
    floorsXML.text = str(floors)
    floorHeightXML = etree.SubElement(building, "floorHeight")
    floorHeightXML.text = str(floorHeight)

    #-- Calculate the "depth" of windows, i.e. embrasure.
    #-- This is also randomised, but fixed for all windows in a building. That's why it is here.
    embrasure = round(random.uniform(0.0, 0.2), 2)
    embXML = etree.SubElement(building, "embrasure")
    embXML.text = str(embrasure)
    #-- Wall thickness (double the embrasure to be consistent)
    if embrasure <= 0.10:
        wallThickness = 0.20
    else:
        wallThickness = 2 * embrasure
    wtXML = etree.SubElement(building, "wallThickness")
    wtXML.text = str(wallThickness)
    #-- Joist (inter-floor thickness)
    joist = round(random.uniform(0.2, 0.3), 2)
    joistXML = etree.SubElement(building, "joist")
    joistXML.text = str(joist)

    #-- Building parts (garages and alcoves)
    if BUILDINGPARTS:
        #-- Percent of buildings that have parts
        percentParts = 80
        if random.randrange(100) > percentParts:
            bpartFilter = False
        else:
            bpartFilter = True
        #-- Only large buildings may have them
        if xs > 4 and ys > 8 and floors in (2, 3) and bpartFilter is True:
            bpart = True
        else:
            bpart = False

        if bpart is True:
            buildingPartXML = etree.SubElement(building, "buildingPart")
            #-- Garage or alcove
            partType = random.choice(['Garage', 'Alcove'])
            partTypeXML = etree.SubElement(buildingPartXML, "partType")
            partTypeXML.text = partType
            #-- Side is always at 1 (East) to make things simpler
            bpartSide = 1
            #-- Dimensions and type of the part
            if partType == 'Garage':
                xgs = round(random.uniform(2, 3), 2)
                ygs = round(random.uniform(4, 5), 2)
                og = round(random.uniform(0.5, 2.0), 2)
            elif partType == 'Alcove':
                xgs = round(random.uniform(.5, 1), 2)
                ygs = round(random.uniform(1.3, 1.9), 2)
                og = .5 * (ys - ygs)
            gorigin = etree.SubElement(buildingPartXML, "partOrigin")
            gorigin.text = str(og)
            pxsize = etree.SubElement(buildingPartXML, "width")
            pxsize.text = str(xgs)
            pysize = etree.SubElement(buildingPartXML, "length")
            pysize.text = str(ygs)
            pzsize = etree.SubElement(buildingPartXML, "height")
            pzsize.text = str(floorHeight)
    else:
    	bpart = False

    #-- Roof, warming up for the real stuff
    roof = etree.SubElement(building, "roof")
    rooftype = etree.SubElement(roof, "roofType")
    #-- Choose the roof type
    if floors <= 3:
        rtype = random.choice(rooftypes)
    #-- Buildings with 4 or more floors can have only a flat roof
    else:
        rtype = 'Flat'
    #-- ... and store it
    rooftype.text = rtype

    #-- Building properties and their storage in the XML
    props = etree.SubElement(building, "properties")
    #-- Roof type as attribute (has to be duplicated not to mess the CityGML generator)
    roofTypeAttXML = etree.SubElement(props, "roofType")
    roofTypeAttXML.text = rtype
    #-- Type of building
    #buildingTypes = ['Residential', 'Office', 'Industrial']
    percentResidential = 80
    btype = etree.SubElement(props, "usage")
    if random.randrange(100) > percentResidential:
        btype.text = "Industrial"
    else:
        btype.text = "Residential"
    #-- Age
    currentYear = 2015
    age = random.randint(1, 70)
    #-- Both year and age are stored because of specific applications
    yearOfConstruction = currentYear - age
    ageXML = etree.SubElement(props, "age")
    ageXML.text = str(age)
    yocXML = etree.SubElement(props, "yearOfConstruction")
    yocXML.text = str(yearOfConstruction)
    #-- Roof clearance
    percentClear = 50
    rclear = etree.SubElement(props, "roofClearance")
    if random.randrange(100) > percentClear:
        rclear.text = "no"
    else:
        rclear.text = "yes"
    #-- Building valuation
    buildingValues = ['1', '2', '3', '4', '5']
    bvXML = etree.SubElement(props, "valuation")
    bvXML.text = random.choice(buildingValues)


    #-- Roof dimensions depending on the type
    if rtype == 'Flat':
        pass
    elif rtype == 'Shed' or rtype == 'Gabled':
        #-- h is the height from the eaves
        h = etree.SubElement(roof, "h")
        if zs > 5.0:
            h.text = str(round(random.uniform(2, 3.8), 2))
        else:
            h.text = str(2.8)
    elif rtype == 'Hipped':
        h = etree.SubElement(roof, "h")
        if zs > 5.0:
            h.text = str(round(random.uniform(2, 3.8), 2))
        else:
            h.text = str(2.8)
        #-- r is not the length of the ridges. It is the length from the eave edge to the ridge
        r = etree.SubElement(roof, "r")
        rwidth = round(random.uniform(0.4,0.5*ys), 2)
        r.text = str(rwidth)
    elif rtype == 'Pyramidal':
        h = etree.SubElement(roof, "h")
        if zs > 5.0:
            h.text = str(round(random.uniform(2, 3.8), 2))
        else:
            h.text = str(2.8)
        #-- Since the pyramidal roof is a special variant of the hipped roof it contains r as well
        r = etree.SubElement(roof, "r")
        rwidth = .5 * ys
        r.text = str(rwidth)
    else:
        raise NameError('No roof type.')

    #-- Overhangs
    overhangs = etree.SubElement(roof, "overhangs")
    #-- Percentage of buildings having overhangs
    percentOverhangs = 80
    xoh = etree.SubElement(overhangs, "xlength")
    yoh = etree.SubElement(overhangs, "ylength")
    if random.randrange(100) > percentOverhangs:
        xoh.text = "0"
        yoh.text = "0"
    else:
        #-- Length in the west-east directions
        xl = round(random.uniform(0.1, 1.0),2)
        xoh.text = str(xl)
        #-- Length in the north-south directions
        yl = round(random.uniform(0.1, 1.0),2)
        if rtype == 'Hipped' or rtype == 'Pyramidal':
            #-- The hipped and pyramidal roof are a bit different. Their Y overhang length is dependant on the X value
            yoh.text = str(xl)
        else:
            yoh.text = str(yl)


    #-- Door
    #-- On which side of the building to put the door?
    if bpart:
        doorSide = list(range(0, 4))
        doorSide.pop(bpartSide)
        doorSide = random.choice(doorSide)
    else:
        doorSide = random.randint(0, 3)
        bpartSide = None
    #-- Door size and coordinates
    doorWidth = round(random.uniform(1.1, 1.5), 2)
    doorHeight = round(random.uniform(1.9, 2.3), 2)
    if doorSide == 0 or doorSide ==  2:
        doorRelativeOrigin = [round(random.uniform(0.1, xs-doorWidth-0.1), 2), round(random.uniform(0.1, 0.3), 2)]
    else:
        doorRelativeOrigin = [round(random.uniform(0.1, ys-doorWidth-0.1), 2), round(random.uniform(0.1, 0.3), 2)]
    #-- Write it in the XML
    door = etree.SubElement(building, "door")
    doorFace = etree.SubElement(door, "wall")
    doorFace.text = str(doorSide)
    #-- Origin of the down left coordinate of the door
    doorOrigin = etree.SubElement(door, "origin")
    doorOriginX = etree.SubElement(doorOrigin, "x")
    doorOriginY = etree.SubElement(doorOrigin, "y")
    doorOriginX.text = str(doorRelativeOrigin[0])
    doorOriginY.text = str(doorRelativeOrigin[1])
    #-- Size of the door
    doorSize = etree.SubElement(door, "size")
    doorSizeX = etree.SubElement(doorSize, "width")
    doorSizeY = etree.SubElement(doorSize, "height")
    doorSizeX.text = str(doorWidth)
    doorSizeY.text = str(doorHeight)

    #-- Procedures for wall windows
    storeyheight = floorHeight
    #-- List of dictionaries
    windows = []
    if zs >= storeyheight:
        nofloors = floors
        
        heightOfOrigin = round(random.uniform(1, 1.5), 2)
        #-- For every side on every floor
        for side in range(0, 4):
            #-- Fixed size windows:
            widthW = round(random.uniform(0.5, 1.49), 2)
            heightW = round(random.uniform(0.3, 1.49), 2)
            if side == 0 or side == 2:
                maxwindows = int(floor(xs / (widthW + 0.2)))
            elif side == 1 or side == 3:
                maxwindows = int(floor(ys / (widthW + 0.2)))
            fixed = [widthW, heightW, maxwindows, heightOfOrigin]
            for fl in range(1, nofloors+1):
                #-- Don't put windows in the same side and on the same floor as the door to avoid overlap
                if side == doorSide and fl == 1:
                    continue
                elif bpart and side == bpartSide and fl == 1:
                    continue
                #-- Number of windows in that wall in that floor
                for result in randomwindow(side, fl, xs, ys, zs, floorHeight, fixed):
                    windows.append(result)


    #-- Store the windows in the XML
    if len(windows) > 0:
        windowsXML = etree.SubElement(building, "windows")
        for w in windows:
            currWindow = etree.SubElement(windowsXML, "window")
            currWindowSide = etree.SubElement(currWindow, "wall")
            currWindowSide.text = str(w['side'])
            currWindowDepth = etree.SubElement(currWindow, "depth")
            currWindowDepth.text = str(embrasure)
            currWindowSize = etree.SubElement(currWindow, "size")
            currWindowWidth = etree.SubElement(currWindowSize, "width")
            currWindowWidth.text = str(w['width'])
            currWindowHeight = etree.SubElement(currWindowSize, "height")
            currWindowHeight.text = str(w['height'])
            currWindowOrigin = etree.SubElement(currWindow, "origin")
            currWindowOriginX = etree.SubElement(currWindowOrigin, "x")
            currWindowOriginX.text = str(w['originX'])
            currWindowOriginY = etree.SubElement(currWindowOrigin, "y")        
            currWindowOriginY.text = str(w['originY'])


    #-- Dormers and roof windows
    #-- Only for larger buildings
    if ys > 4:
        #-- Random choice do we put them or not?
        selection = random.randint(0, 2)
        if selection == 0:
            # No roof dormer or window 
            pass
        elif selection == 1 and rtype != 'Flat': #-- Disregard flat roofs
            #-- Only if height from the eaves to the top is >3.0 m
            if float(h.text) > 3.0:
                #-- Dormer generation
                if (rtype == 'Hipped' or rtype == 'Pyramidal'):
                    if xs > 4:
                        dormers = dormer(rtype, xs, ys, zs, rwidth)
                    else:
                        dormers = []
                else:
                    dormers = dormer(rtype, xs, ys, zs)
                #-- Dormer storage
                if len(dormers) > 0:
                    dormersXML = etree.SubElement(roof, "dormers")
                for dor in dormers:
                    currDormer = etree.SubElement(dormersXML, "dormer")
                    currDormerSide = etree.SubElement(currDormer, "side")
                    currDormerSide.text = str(dor['side'])
                    currDormerSize = etree.SubElement(currDormer, "size")
                    currDormerWidth = etree.SubElement(currDormerSize, "width")
                    currDormerWidth.text = str(dor['dormerWidth'])
                    currDormerHeight = etree.SubElement(currDormerSize, "height")
                    currDormerHeight.text = str(dor['dormerHeight'])                
                    currDormerOrigin = etree.SubElement(currDormer, "origin")
                    currDormerOriginX = etree.SubElement(currDormerOrigin, "x")
                    currDormerOriginX.text = str(dor['dormerOriginX'])
                    currDormerOriginY = etree.SubElement(currDormerOrigin, "y")        
                    currDormerOriginY.text = str(dor['dormerOriginY'])                

        #-- Let's put a roof window instead
        elif selection == 2:
            rfwindows = None
            if rtype == 'Hipped' or rtype == 'Pyramidal':
                if float(h.text) > 3.0:
                    rfwindows = roofwindow(rtype, xs, ys, zs, h, rwidth)
            elif rtype == 'Gabled':
                if float(h.text) > 3.0:
                    rfwindows = roofwindow(rtype, xs, ys, zs, h)
            else:
                rfwindows = roofwindow(rtype, xs, ys, zs)
            if rfwindows is not None and len(rfwindows) > 0:
                rfwindowsXML = etree.SubElement(roof, "roofWindows")
                for rfw in rfwindows:
                    currRfWin = etree.SubElement(rfwindowsXML, "roofWindow")
                    currRfWinSide = etree.SubElement(currRfWin, "side")
                    currRfWinSide.text = str(rfw['side'])
                    currRfWinSize = etree.SubElement(currRfWin, "size")
                    currRfWinWidth = etree.SubElement(currRfWinSize, "width")
                    currRfWinWidth.text = str(rfw['rfwinWidth'])
                    currRfWinHeight = etree.SubElement(currRfWinSize, "height")
                    currRfWinHeight.text = str(rfw['rfwinHeight'])                
                    currRfWinOrigin = etree.SubElement(currRfWin, "origin")
                    currRfWinOriginX = etree.SubElement(currRfWinOrigin, "x")
                    currRfWinOriginX.text = str(rfw['rfwinOriginX'])
                    currRfWinOriginY = etree.SubElement(currRfWinOrigin, "y")        
                    currRfWinOriginY.text = str(rfw['rfwinOriginY']) 
        else:
            pass


    #-- Chimneys
    if ys > 5 and xs > 5:
        #-- How many such buildings have the chimney
        percentChimneys = 80
        go = True
        if (rtype == 'Hipped' or rtype == 'Pyramidal') and ((xs - 2*rwidth) < 1):
            go = False
        if random.randrange(100) > percentChimneys and go:
            chimney = etree.SubElement(roof, "chimney")
            #-- Where is the chimney located?
            cside = etree.SubElement(chimney, "side")
            #-- Size of the chimney
            chimneySize = etree.SubElement(chimney, "size")
            cwidth = round(random.uniform(0.2, 0.4), 2)
            cheight = round(random.uniform(0.5, 1.5), 2)
            cx = etree.SubElement(chimneySize, "width")
            #cy = etree.SubElement(chimney, "ylength")
            ch = etree.SubElement(chimneySize, "height")
            cx.text = str(cwidth)
            #cy.text = str(cwidth)
            ch.text = str(cheight)
            #-- Randomise position of the chimney
            cOrigin = etree.SubElement(chimney, "origin")
            cOriginX = etree.SubElement(cOrigin, "x")
            cOriginY = etree.SubElement(cOrigin, "y")
            #-- Minimum distance from the edge of the roof
            edgeThreshold = 0.1
            if rtype == 'Shed':
                csidechoice = 1
                cOriginXchoice = round(random.uniform(edgeThreshold, ys - edgeThreshold - cwidth), 2)
                cOriginYchoice = xs - edgeThreshold - cwidth
            elif rtype == 'Flat':
                #-- Randomise the side of the roof where the chimney will be positioned
                chimneyPos = random.choice([0, 1, 2, 3, 4])
                csidechoice = 1
                if chimneyPos == 0:
                    cOriginXchoice = edgeThreshold
                    cOriginYchoice = xs - edgeThreshold - cwidth
                elif chimneyPos == 1:
                    cOriginXchoice = edgeThreshold
                    cOriginYchoice = edgeThreshold
                elif chimneyPos == 2:
                    cOriginXchoice = ys - edgeThreshold - cwidth
                    cOriginYchoice = edgeThreshold
                elif chimneyPos == 3:
                    cOriginXchoice = ys - edgeThreshold - cwidth
                    cOriginYchoice = xs - edgeThreshold - cwidth
                elif chimneyPos == 4:
                    cOriginXchoice = round(float(ys)/2.0, 2) - cwidth#round(cwidth/2.0, 2)
                    cOriginYchoice = round(float(xs)/2.0, 2) - cwidth#round(cwidth/2.0, 2)
            elif rtype == 'Gabled':
                csidechoice = random.choice([1,3])
                if csidechoice == 1:
                    cOriginXchoice = round(random.uniform(edgeThreshold, ys - edgeThreshold - cwidth), 2)
                    cOriginYchoice = round(float(xs)/2.0, 2) - cwidth - edgeThreshold# round(cwidth/2.0, 2) - edgeThreshold
                elif csidechoice == 3:
                    cOriginXchoice = round(random.uniform(edgeThreshold, ys - edgeThreshold - cwidth), 2)
                    cOriginYchoice = round(float(xs)/2.0, 2) - cwidth - edgeThreshold#round(cwidth/2.0, 2) - edgeThreshold
            elif rtype == 'Hipped' or rtype == 'Pyramidal':
                csidechoice = random.choice([1,3])
                if csidechoice == 1:
                    cOriginXchoice = round(random.uniform(rwidth + edgeThreshold, ys - rwidth - cwidth - edgeThreshold), 2)
                    cOriginYchoice = round(float(xs)/2.0, 2) - cwidth - edgeThreshold# round(cwidth/2.0, 2) - edgeThreshold
                elif csidechoice == 3:
                    cOriginXchoice = round(random.uniform(rwidth + edgeThreshold, ys - rwidth - cwidth - edgeThreshold), 2)
                    cOriginYchoice = round(float(xs)/2.0, 2) - cwidth - edgeThreshold# - round(cwidth/2.0, 2) - edgeThreshold

            cside.text = str(csidechoice)
            cOriginX.text = str(cOriginXchoice)
            cOriginY.text = str(cOriginYchoice)

    #-- That's it for the building
    #-- Return the position of the building in the grid
    return o[3]

def dormer(rtype, xs, ys, zs, r=None):
    """Randomise a dormer."""
    dormers = []
    if rtype == 'Gabled':
        #-- For smaller roofs permit one dormer on each side. For larger up to 2
        if ys < 6:
            nodormers = 1
        else:
            nodormers = random.randint(1, 2)
        dormerWidth = round(random.uniform(.8,1.3), 2)
        dormerHeight = round(random.uniform(1,1.2), 2)  
        dormerOriginY = round(random.uniform(0.3, 1.0), 2)  
        for i in range(0, nodormers):
            if nodormers == 1:
                dormerOriginX = round(float(ys)/2.0 ,2) - round(dormerWidth/2.0, 2)
            elif nodormers == 2:
                if i == 0:
                    dormerOriginX = round(float(ys)/4.0, 2) - round(dormerWidth/2.0, 2)
                elif i == 1:
                    dormerOriginX = round(float(ys)/2.0, 2) + round(float(ys)/4.0, 2) - round(dormerWidth/2.0, 2)

            thisdormer1 = {'dormerWidth' : dormerWidth, 'dormerHeight' : dormerHeight, 'dormerOriginX': dormerOriginX, 'dormerOriginY' : dormerOriginY, 'side' : 1}
            thisdormer2 = {'dormerWidth' : dormerWidth, 'dormerHeight' : dormerHeight, 'dormerOriginX': dormerOriginX, 'dormerOriginY' : dormerOriginY, 'side' : 3}
            dormers.append(thisdormer1)
            dormers.append(thisdormer2)

    elif rtype == 'Shed':
        if ys < 6:
            nodormers = 1
        else:
            nodormers = random.randint(1, 2)
        dormerWidth = round(random.uniform(.8,1.3), 2)
        dormerHeight = round(random.uniform(1,1.2), 2)  
        dormerOriginY = round(random.uniform(0.3, 1.0), 2)  
        for i in range(0, nodormers):
            if nodormers == 1:
                dormerOriginX = round(float(ys)/2.0, 2) - round(dormerWidth/2.0, 2)
            elif nodormers == 2:
                if i == 0:
                    dormerOriginX = round(float(ys)/4.0, 2) - round(dormerWidth/2.0, 2)
                elif i == 1:
                    dormerOriginX = round(float(ys)/2.0, 2) + round(float(ys)/4.0, 2) - round(dormerWidth/2.0, 2)

            thisdormer1 = {'dormerWidth' : dormerWidth, 'dormerHeight' : dormerHeight, 'dormerOriginX': dormerOriginX, 'dormerOriginY' : dormerOriginY, 'side' : 1}
            dormers.append(thisdormer1)

    elif rtype == 'Hipped' or rtype == 'Pyramidal':
        if ys < 6:
            nodormers = 1
        else:
            nodormers = 1#random.randint(1, 2)
        dormerWidth = round(random.uniform(.8, 1.3), 2)
        dormerHeight = round(random.uniform(.8, 1.0), 2)  
        dormerOriginY = round(random.uniform(0.3, 0.8), 2)  
        for i in range(0, nodormers):
            if nodormers == 1:
                dormerOriginX = round(float(ys)/2.0 ,2) - round(dormerWidth/2.0, 2)
            elif nodormers == 2:
                if i == 0:
                    dormerOriginX = round(float(ys)/4.0, 2) - round(dormerWidth/2.0, 2)
                elif i == 1:
                    dormerOriginX = round(float(ys)/2.0, 2) + round(float(ys)/4.0, 2) - round(dormerWidth/2.0, 2)

            thisdormer1 = {'dormerWidth' : dormerWidth, 'dormerHeight' : dormerHeight, 'dormerOriginX': dormerOriginX, 'dormerOriginY' : dormerOriginY, 'side' : 1}
            thisdormer2 = {'dormerWidth' : dormerWidth, 'dormerHeight' : dormerHeight, 'dormerOriginX': dormerOriginX, 'dormerOriginY' : dormerOriginY, 'side' : 3}            
            dormers.append(thisdormer1)
            dormers.append(thisdormer2)
        if r > 1 and xs > 4:
            if xs < 6:
                nodormers = 1
            else:
                nodormers = 1 #random.randint(1, 2)
            for i in range(0, nodormers):
                if nodormers == 1:
                    dormerOriginX = round(float(xs)/2.0, 2) - round(dormerWidth/2.0, 2)
                elif nodormers == 2:
                    if i == 0:
                        dormerOriginX = round(float(xs)/4.0, 2) - round(dormerWidth/2.0, 2)
                    elif i == 1:
                        dormerOriginX = round(float(xs)/2.0, 2) + round(float(xs)/4.0, 2) - round(dormerWidth/2.0, 2)

                thisdormer1 = {'dormerWidth' : dormerWidth, 'dormerHeight' : dormerHeight, 'dormerOriginX': dormerOriginX, 'dormerOriginY' : dormerOriginY, 'side' : 0}
                thisdormer2 = {'dormerWidth' : dormerWidth, 'dormerHeight' : dormerHeight, 'dormerOriginX': dormerOriginX, 'dormerOriginY' : dormerOriginY, 'side' : 2}            
                dormers.append(thisdormer1)
                dormers.append(thisdormer2)

    elif rtype == 'Flat':
        pass

    return dormers

def roofwindow(rtype, xs, ys, zs, h=None, r=None):
    """Procedural modelling of roof windows, similar as to dormers."""
    roofwindow = []
    if rtype == 'Gabled':
        if ys < 6:
            norfwins = 1
        else:
            norfwins = random.randint(1, 2)
        if float(h.text) > 3.0:
            rfwinWidth = round(random.uniform(.8,1.3), 2)
            rfwinHeight = round(random.uniform(1,1.2), 2)  
            rfwinOriginY = round(random.uniform(0.1, 1.0), 2) 
        else:
            rfwinWidth = round(random.uniform(.5,1.0), 2)
            rfwinHeight = round(random.uniform(.5,1.0), 2)  
            rfwinOriginY = round(random.uniform(0.1, 0.5), 2)  
        for i in range(0, norfwins):
            if norfwins == 1:
                rfwinOriginX = round(float(ys)/2.0 ,2) - round(rfwinWidth/2.0, 2)
            elif norfwins == 2:
                if i == 0:
                    rfwinOriginX = round(float(ys)/4.0, 2) - round(rfwinWidth/2.0, 2)
                elif i == 1:
                    rfwinOriginX = round(float(ys)/2.0, 2) + round(float(ys)/4.0, 2) - round(rfwinWidth/2.0, 2)

            thisrfwin1 = {'rfwinWidth' : rfwinWidth, 'rfwinHeight' : rfwinHeight, 'rfwinOriginX': rfwinOriginX, 'rfwinOriginY' : rfwinOriginY, 'side' : 1}
            thisrfwin2 = {'rfwinWidth' : rfwinWidth, 'rfwinHeight' : rfwinHeight, 'rfwinOriginX': rfwinOriginX, 'rfwinOriginY' : rfwinOriginY, 'side' : 3}
            roofwindow.append(thisrfwin1)
            roofwindow.append(thisrfwin2)

    elif rtype == 'Shed':
        if ys < 6:
            norfwins = 1
        else:
            norfwins = random.randint(1, 2)
        rfwinWidth = round(random.uniform(.8,1.3), 2)
        rfwinHeight = round(random.uniform(1,1.2), 2)  
        rfwinOriginY = round(random.uniform(0.1, 1.0), 2)  
        for i in range(0, norfwins):
            if norfwins == 1:
                rfwinOriginX = round(float(ys)/2.0 ,2) - round(rfwinWidth/2.0, 2)
            elif norfwins == 2:
                if i == 0:
                    rfwinOriginX = round(float(ys)/4.0, 2) - round(rfwinWidth/2.0, 2)
                elif i == 1:
                    rfwinOriginX = round(float(ys)/2.0, 2) + round(float(ys)/4.0, 2) - round(rfwinWidth/2.0, 2)

            thisrfwin1 = {'rfwinWidth' : rfwinWidth, 'rfwinHeight' : rfwinHeight, 'rfwinOriginX': rfwinOriginX, 'rfwinOriginY' : rfwinOriginY, 'side' : 1}
            roofwindow.append(thisrfwin1)

    elif rtype == 'Hipped' or rtype == 'Pyramidal':
        if ys < 6:
            norfwins = 1
        else:
            norfwins = 1#random.randint(1, 2)
        rfwinWidth = round(random.uniform(.8,1.3), 2)
        rfwinHeight = round(random.uniform(1,1.2), 2)  
        rfwinOriginY = round(random.uniform(0.1, 1.0), 2)  
        for i in range(0, norfwins):
            if norfwins == 1:
                rfwinOriginX = round(float(ys)/2.0 ,2) - round(rfwinWidth/2.0, 2)
            elif norfwins == 2:
                if i == 0:
                    rfwinOriginX = round(float(ys)/4.0, 2) - round(rfwinWidth/2.0, 2)
                elif i == 1:
                    rfwinOriginX = round(float(ys)/2.0, 2) + round(float(ys)/4.0, 2) - round(rfwinWidth/2.0, 2)

            thisrfwin1 = {'rfwinWidth' : rfwinWidth, 'rfwinHeight' : rfwinHeight, 'rfwinOriginX': rfwinOriginX, 'rfwinOriginY' : rfwinOriginY, 'side' : 1}
            thisrfwin2 = {'rfwinWidth' : rfwinWidth, 'rfwinHeight' : rfwinHeight, 'rfwinOriginX': rfwinOriginX, 'rfwinOriginY' : rfwinOriginY, 'side' : 3}            
            roofwindow.append(thisrfwin1)
            roofwindow.append(thisrfwin2)

        if r > 1 and xs > 4:
            if xs < 6:
                norfwins = 1
            else:
                norfwins = 1 #random.randint(1, 2)
            for i in range(0, norfwins):
                if norfwins == 1:
                    rfwinOriginX = round(float(xs)/2.0, 2) - round(rfwinWidth/2.0, 2)
                elif norfwins == 2:
                    if i == 0:
                        rfwinOriginX = round(float(xs)/4.0, 2) - round(rfwinWidth/2.0, 2)
                    elif i == 1:
                        rfwinOriginX = round(float(xs)/2.0, 2) + round(float(xs)/4.0, 2) - round(rfwinWidth/2.0, 2)

                thisrfwin1 = {'rfwinWidth' : rfwinWidth, 'rfwinHeight' : rfwinHeight, 'rfwinOriginX': rfwinOriginX, 'rfwinOriginY' : rfwinOriginY, 'side' : 0}
                thisrfwin2 = {'rfwinWidth' : rfwinWidth, 'rfwinHeight' : rfwinHeight, 'rfwinOriginX': rfwinOriginX, 'rfwinOriginY' : rfwinOriginY, 'side' : 2}            
                roofwindow.append(thisrfwin1)
                roofwindow.append(thisrfwin2)

    elif rtype == 'Flat':
        if ys < 6:
            norfwins = 2
        else:
            norfwins = random.choice([2, 4])
        rfwinWidth = round(random.uniform(.8,1.2), 2)
        rfwinHeight = round(random.uniform(1,1.2), 2)  
        rfwinOriginY = round(random.uniform(0.5, 1.0), 2)  
        for i in range(0, norfwins):
            if norfwins == 2:
                rfwinOriginX = round(float(ys)/2.0, 2) - round(rfwinWidth/2.0, 2)
                if i == 0:
                    thisrfwin1 = {'rfwinWidth' : rfwinWidth, 'rfwinHeight' : rfwinHeight, 'rfwinOriginX': rfwinOriginX, 'rfwinOriginY' : rfwinOriginY, 'side' : 1}
                elif i == 1:
                    rfwoy_second = float(xs) - rfwinHeight - rfwinOriginY
                    thisrfwin1 = {'rfwinWidth' : rfwinWidth, 'rfwinHeight' : rfwinHeight, 'rfwinOriginX': rfwinOriginX, 'rfwinOriginY' : rfwoy_second, 'side' : 1}
            elif norfwins == 4:
                if i == 0 or i == 2:
                    if i == 0:
                        rfwinOriginX = round(float(ys)/4.0, 2) - round(rfwinWidth/2.0, 2)
                    elif i == 2:
                        rfwinOriginX = 3*round(float(ys)/4.0, 2) - round(rfwinWidth/2.0, 2)
                    thisrfwin1 = {'rfwinWidth' : rfwinWidth, 'rfwinHeight' : rfwinHeight, 'rfwinOriginX': rfwinOriginX, 'rfwinOriginY' : rfwinOriginY, 'side' : 1}
                elif i == 1 or i == 3:
                    if i == 1:
                        rfwinOriginX = round(float(ys)/4.0, 2) - round(rfwinWidth/2.0, 2)#round(float(ys)/2.0, 2) + round(float(ys)/4.0, 2) - round(rfwinWidth/2.0, 2)
                    elif i == 3:
                        rfwinOriginX = round(float(ys)/2.0, 2) + round(float(ys)/4.0, 2) - round(rfwinWidth/2.0, 2)
                    rfwoy_second = float(xs) - rfwinHeight - rfwinOriginY
                    thisrfwin1 = {'rfwinWidth' : rfwinWidth, 'rfwinHeight' : rfwinHeight, 'rfwinOriginX': rfwinOriginX, 'rfwinOriginY' : rfwoy_second, 'side' : 1}

            roofwindow.append(thisrfwin1)

    return roofwindow


def randomwindow(side, fl, xs, ys, zs, floorHeight, fixed=None):
    """Randomly generate windows of a building. If fixed, use these dimensions."""
    res = []
    
    if fixed:
        #-- Determine the number of windows, their origin and side
        if side == 0 or side == 2:

            w = {}
            w['width'] = fixed[0]
            w['height'] = fixed[1]
            maxwindows = fixed[2]
            woriginY = (fl - 1) * floorHeight + fixed[3]
            nowindows = random.randint(1, maxwindows)
            firstW = round((xs - maxwindows * w['width'])/float(maxwindows + 1), 2)
            for i in range(1, nowindows+1):
                if i == 0:
                    continue
                w = {}
                w['width'] = fixed[0]
                w['height'] = fixed[1]             
                if nowindows > 1:
                    distW = round((xs - nowindows * w['width'] - 2 * firstW)/float(nowindows - 1), 2)
                else:
                    distW = 0
                w['originX'] = firstW + (i - 1) * distW + (i - 1) * w['width']
                w['originY'] = woriginY
                w['side'] = str(side)
                res.append(w)

        elif side == 1 or side == 3:

            w = {}
            w['width'] = fixed[0]
            w['height'] = fixed[1]
            maxwindows = fixed[2]
            woriginY = (fl - 1) * floorHeight + fixed[3]
            nowindows = random.randint(1, maxwindows)
            firstW = round((ys - maxwindows * w['width'])/float(maxwindows + 1), 2)
            for i in range(1, nowindows+1):
                if i == 0:
                    continue
                w = {}
                w['width'] = fixed[0]
                w['height'] = fixed[1]
                if nowindows > 1:
                    distW = round((ys - nowindows * w['width'] - 2 * firstW)/float(nowindows - 1), 2)
                else:
                    distW = 0
                w['originX'] = firstW + (i - 1) * distW + (i - 1) * w['width']
                w['originY'] = woriginY
                w['side'] = str(side)
                res.append(w)

        return res

    else:
        raise ValueError("Not supported at the moment")
        #-- Determine the number of windows
        if side == 0 or side == 2:
            if xs <= 3:
                #-- Same originY for all windows on that side of the building on that floor
                woriginY = (fl-1) * 3 + round(random.uniform(1,1.5), 2)
                nowindows = random.randint(0, 1)
                for i in range(0, nowindows+1):
                    if i == 0:
                        continue
                    w = {}
                    w['width'] = round(random.uniform(0.3,2), 2)
                    w['height'] = round(random.uniform(0.3,2), 2)
                    w['originX'] = round(random.uniform(0.1,xs-w['width']-0.1), 2)
                    w['originY'] = woriginY
                    w['side'] = str(side)
                    res.append(w)
            elif xs > 3:
                woriginY = (fl-1) * 3 + round(random.uniform(1,1.5), 2)
                nowindows = random.randint(1, 3)
                print(nowindows)
                for i in range(1, nowindows+1):
                    if i == 0:
                        continue
                    w = {}
                    w['width'] = round(random.uniform(0.3,2), 2)
                    w['height'] = round(random.uniform(0.3,2), 2)
                    #w['originX'] = round(random.uniform(0.1,i*.5*(xs/float(nowindows))-w['width']-0.1), 2)
                    w['originX'] = round(random.uniform(0.1 + (i-1) * (xs/float(nowindows)), i*(xs/float(nowindows))-w['width']-0.1), 2)
                    w['originY'] = woriginY
                    w['side'] = str(side)
                    res.append(w)

        elif side == 1 or side == 3:
            if ys <= 3:
                woriginY = (fl-1) * 3 + round(random.uniform(1,1.5), 2)
                nowindows = random.randint(0, 1)
                for i in range(0, nowindows+1):
                    if i == 0:
                        continue                
                    w = {}
                    w['width'] = round(random.uniform(0.3,2), 2)
                    w['height'] = round(random.uniform(0.3,2), 2)
                    w['originX'] = round(random.uniform(0.1,ys-w['width']-0.1), 2)
                    w['originY'] = woriginY
                    w['side'] = str(side)
                    res.append(w)
            elif ys > 3:
                woriginY = (fl-1) * 3 + round(random.uniform(1,1.5), 2)
                nowindows = random.randint(1, 3)
                print(nowindows)
                for i in range(1, nowindows+1):
                    if i == 0:
                        continue               
                    w = {}
                    w['width'] = round(random.uniform(0.3,1.0), 2)
                    w['height'] = round(random.uniform(0.3,1.0), 2)
                    w['originX'] = round(random.uniform(0.1 + (i-1) * (ys/float(nowindows)), i*(ys/float(nowindows))-w['width']-0.1), 2)
                    print(i, w['originX'])
                    w['originY'] = woriginY
                    w['side'] = str(side)
                    res.append(w)

        return res

def arranger(i, n, crs = None):
    """Arranges the location of each building."""
    if crs is not None:
        if crs == 'Nordoostpolder':
            shiftx = 173469.0
            shifty = 526427.0
        else:
            shiftx = 0.0
            shifty = 0.0
    else:
        shiftx = 0.0
        shifty = 0.0
    """Arrange the models in a grid."""
    i += 1
    if i > n:
        raise NameError("i cannot be bigger than n.")
    #-- Size of the grid (translate the number of buildings to a square)
    gridsize = int(round(sqrt(n),0))
    #-- Size of the grid cells
    sx = CELLSIZE
    sy = CELLSIZE
    column = trunc(float(i-1)/float(gridsize))
    if column > 0:
        row = i % (gridsize * column + 1)
    elif column == 0:
        row = i - 1
    return shiftx + column*sx, shifty + row*sy, 0, [column, row]


def streetgenerator(specs, CELLSIZE, grid, skipx, skipy):
    """Generate a road network. Input: size of each cell for buildings, 
    size of the grid, the number of streets to skip in each direction 
    (so not every building is bounded by four streets, looks to dense)."""
    width = 5.0
    separation = 1.0
    row = grid[0]
    col = grid[1]
    networkoutline = [[-width - separation, -width - separation], [row * CELLSIZE + CELLSIZE + width, col * CELLSIZE + CELLSIZE + width]]
    holes = []
    for r in range(0, row+1, skipx):
        for c in range(0, col+1, skipy):
            p0x = r * CELLSIZE - separation
            if (r + skipx) * CELLSIZE - separation - width >= row * CELLSIZE:
                p1x = row * CELLSIZE + CELLSIZE
            else:
                p1x = (r + skipx) * CELLSIZE - separation - width
            p0y = c * CELLSIZE - separation
            if (c + skipy) * CELLSIZE - separation - width >= col * CELLSIZE:
                p1y = col * CELLSIZE + CELLSIZE
            else:
                p1y = (c + skipy) * CELLSIZE - separation - width
            holes.append([[p0x, p0y], [p1x, p1y]])

    streetnetwork = etree.SubElement(specs, "streets")
    outline = etree.SubElement(streetnetwork, "outline")
    outline.text = str(networkoutline[0][0]) + ' ' + str(networkoutline[0][1]) + ' ' + str(networkoutline[1][0]) + ' ' + str(networkoutline[1][1])
    holesXML = etree.SubElement(streetnetwork, "holes")
    for h in holes:
        hXML = etree.SubElement(holesXML, "hole")
        hXML.text = str(h[0][0]) + ' ' + str(h[0][1]) + ' ' + str(h[1][0]) + ' ' + str(h[1][1])
    return specs

def vegetationgenerator(specs, CELLSIZE, vgcells, n):
    """Generate vegetation (parks instead of buildings)."""
    width = 5.0
    separation = 1.0
    height = 3.0
    parks = etree.SubElement(specs, "parks")
    for v in vgcells:
        park = etree.SubElement(parks, "park")
        parkoutline = etree.SubElement(park, "outline")
        parkheight = etree.SubElement(park, "height")
        parkheight.text = str(height)
        o = arranger(v, n)
        parkoutline.text = str(float(o[0])-separation) + ' ' + str(float(o[1])-separation) + ' ' + str(float(o[0]) + CELLSIZE - width - separation) + ' ' + str(float(o[1]) + CELLSIZE - width - separation)
    return specs

#---- Program start

#-- If there is no input of the number of buildinds then default to 1000
if NUMBEROFBUILDINGS:
    n = int(NUMBEROFBUILDINGS)
else:
    n = 1000
#-- Where to write the XML containing building information
if FILENAME:
    fname = str(FILENAME)
else:
    fname = "BuildingInformation.xml"

#-- Place parks
if VEGETATION:
    #- Ratio of parks in the cells
    rvgs = 0.05
    nvgs = int(round(rvgs * float(n), 0))
    vgcells = []
    allcells = list(range(n))
    for vgs in range(0, nvgs):
        vgcells.append(random.choice(allcells))
else:
    vgcells = False
#-- Generate the buildings
bspecs, cell = buildinggenerator(n, vgcells, CRS)
#-- Generate streets
if STREETS:
    bspecs = streetgenerator(bspecs, CELLSIZE, cell, 3, 3)
#-- Generate the vegetation
if VEGETATION:
    bspecs = vegetationgenerator(bspecs, CELLSIZE, vgcells, n)
#-- Write the specs in an XML form
buildings = etree.tostring(bspecs, pretty_print=True)
#-- Write the XML file from the string
SpecFile = open(fname, "w")
#-- Add the header to be politically correct
SpecFile.write("<?xml version=\"1.0\" encoding=\"utf-8\"?>\n")
SpecFile.write("<!-- Generated by Random3Dcity (http://github.com/tudelft3d/Random3Dcity), a tool developed by Filip Biljecki at TU Delft. Version: 2015-03-11. -->\n")
#SpecFile.write(buildings)
SpecFile.write(buildings.decode('utf-8'))
SpecFile.close()
#-- Done
print('XML with buildings written in file', fname)