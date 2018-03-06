#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

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
Generate CityGML files according to the building XML specifications.
"""

from lxml import etree
import argparse
import random
import numpy
import math
import uuid
import copy


#-- Parse command-line arguments
PARSER = argparse.ArgumentParser(description='Generator of CityGML files according to the XML of buildings.')
PARSER.add_argument('-i', '--filename',
    help='XML file to read', required=True)
PARSER.add_argument('-o', '--directory',
    help='Directory where to write CityGMLs', required=True)
PARSER.add_argument('-r', '--rotation',
    help='Enable rotation (default is true; allowed values 0/1, True/False)', required=False)
PARSER.add_argument('-p', '--parts',
    help='Enable building parts (default is true; allowed values 0/1, True/False)', required=False)
PARSER.add_argument('-id', '--id',
    help='Generate an UUID for each polygon.', required=False)
PARSER.add_argument('-gr', '--geometricref',
    help='Generate all geometric references (variants within LODs).', required=False)
PARSER.add_argument('-ov', '--solids',
    help='Generate solids and semantic variants (ov = other variants).', required=False)
PARSER.add_argument('-s', '--street',
    help='Generate a road network.', required=False)
PARSER.add_argument('-v', '--vegetation',
    help='Generate vegetation.', required=False)
PARSER.add_argument('-rp', '--report',
    help='Report on the progress. Disable with Python3.', required=False)

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

ARGS = vars(PARSER.parse_args())
BUILDINGFILE = ARGS['filename']
DIRECTORY = ARGS['directory']
ROTATIONENABLED = argRead(ARGS['rotation'], True)
BUILDINGPARTS = argRead(ARGS['parts'], True)
ASSIGNID = argRead(ARGS['id'], True)
VARIANTS = argRead(ARGS['geometricref'], False)
SOLIDS = argRead(ARGS['solids'], False)
STREETS = argRead(ARGS['street'], False)
VEGETATION = argRead(ARGS['vegetation'], False)
REPORT = argRead(ARGS['report'], True)

if REPORT:
    try:
        from fish import ProgressFish
    except:
        print("--Package Fish (used for reporting) failed to load, hence reporting is disabled--")
        #-- Just disable reporting if Fish fails to load
        REPORT = False

#-- Name spaces
ns_citygml = "http://www.opengis.net/citygml/2.0"

ns_gml = "http://www.opengis.net/gml"
ns_bldg = "http://www.opengis.net/citygml/building/2.0"
ns_tran = "http://www.opengis.net/citygml/transportation/2.0"
ns_veg = "http://www.opengis.net/citygml/vegetation/2.0"
ns_xsi = "http://www.w3.org/2001/XMLSchema-instance"
ns_xAL = "urn:oasis:names:tc:ciq:xsdschema:xAL:2.0"
ns_xlink = "http://www.w3.org/1999/xlink"
ns_dem = "http://www.opengis.net/citygml/relief/2.0"
ns_fme = "http://www.safe.com/xml/xmltables"

nsmap = {
    None: ns_citygml,
    'gml': ns_gml,
    'bldg': ns_bldg,
    'tran': ns_tran,
    'veg': ns_veg,
    'xsi': ns_xsi,
    'xAL': ns_xAL,
    'xlink': ns_xlink,
    'dem': ns_dem,
    'fme': ns_fme
}


#-- Functions

def createCityGML(suffix):
    """Creates a CityGML foundation to be filled later by the remaining part of the script."""
    CityModel = etree.Element("CityModel", nsmap=nsmap)
    citymodelname = etree.SubElement(CityModel, "{%s}name" % ns_gml)
    citymodelname.text = str(suffix)
    boundedBy = etree.SubElement(CityModel, "{%s}boundedBy" % ns_gml)
    Envelope = etree.SubElement(boundedBy, "{%s}Envelope" % ns_gml, srsDimension="3")
    Envelope.attrib["srsName"] = "EPSG:28992"
    lowercorner = etree.SubElement(Envelope, "{%s}lowerCorner" % ns_gml)
    lowercorner.text = '0 0 0'
    uppercorner = etree.SubElement(Envelope, "{%s}upperCorner" % ns_gml)
    uppercorner.text = '4000 4000 25'
    return CityModel


def storeCityGML(suffix):
    "Write the CityGML file."
    citygml = etree.tostring(CityGMLs[suffix], pretty_print=True)
    #-- Write the CityGML file
    if str(suffix) == 'Ground Truth':
        fname = DIRECTORY + '/' + 'groundTruth.gml'
    else:
        fname = DIRECTORY + '/' + str(suffix) + '.gml'
    citygmlFile = open(fname, "w")
    #-- Header of the XML
    citygmlFile.write("<?xml version=\"1.0\" encoding=\"utf-8\"?>\n")
    citygmlFile.write("<!-- Generated by Random3Dcity (http://github.com/tudelft3d/Random3Dcity), a tool developed by Filip Biljecki at TU Delft. Version: 2015-03-11. -->\n")
    # citygmlFile.write(citygml)
    citygmlFile.write(citygml.decode('utf-8'))
    citygmlFile.close()


def verticesBody(o, x, y, z, h=None, top=None, override=None):
    """Calculates the vertices of the building block/body depending on the input."""
    #-- If the h value is not supplied than it is zero
    if not h:
         h = 0.0
    if top:
        if top < 1.5:
            z = z + float(top) * h
    elif top is None:
            if override:
                z = override
            else:
                z = z + h

    p = []
    p0 = "%s %s %s" % (o[0],o[1],o[2])
    p.append(p0)
    p1 = "%s %s %s" % (o[0]+x,o[1],o[2])
    p.append(p1)
    p2 = "%s %s %s" % (o[0]+x,o[1]+y,o[2])
    p.append(p2)
    p3 = "%s %s %s" % (o[0],o[1]+y,o[2])
    p.append(p3)
    p4 = "%s %s %s" % (o[0],o[1],o[2]+z)
    p.append(p4)
    p5 = "%s %s %s" % (o[0]+x,o[1],o[2]+z)
    p.append(p5)
    p6 = "%s %s %s" % (o[0]+x,o[1]+y,o[2]+z)
    p.append(p6)
    p7 = "%s %s %s" % (o[0],o[1]+y,o[2]+z)
    p.append(p7)

    return p


def verticesBodyList(o, x, y, z, h=None, top=None):
    """Calculates the vertices of the building block/body as a list depending on the input. Redundant function."""
    #-- If the h value is not supplied than it is zero
    if not h:
         h = 0.0
    if top:
        z = z + float(top) * h

    p = []
    p0 = [o[0],o[1],o[2]]
    p.append(p0)
    p1 = [o[0]+x,o[1],o[2]]
    p.append(p1)
    p2 = [o[0]+x,o[1]+y,o[2]]
    p.append(p2)
    p3 = [o[0],o[1]+y,o[2]]
    p.append(p3)
    p4 = [o[0],o[1],o[2]+z]
    p.append(p4)
    p5 = [o[0]+x,o[1],o[2]+z]
    p.append(p5)
    p6 = [o[0]+x,o[1]+y,o[2]+z]
    p.append(p6)
    p7 = [o[0],o[1]+y,o[2]+z]
    p.append(p7)
    return p


def verticesRoof(b, h, rtype, width=None):
    """Calculates the vertices of the building roof."""
    #-- The basic information
    o, x, y, z = b
    #-- If no roof
    if not h:
        h = 0.0
    #-- Roof points
    r = []
    if rtype == 'Gabled':
        r0 = "%s %s %s" % (o[0]+.5*x, o[1], o[2]+z+h)
        r.append(r0)
        r1 = "%s %s %s" % (o[0]+.5*x, o[1]+y, o[2]+z+h)
        r.append(r1)
    elif rtype == 'Shed':
        r0 = "%s %s %s" % (o[0], o[1], o[2]+z+h)
        r.append(r0)
        r1 = "%s %s %s" % (o[0], o[1]+y, o[2]+z+h)
        r.append(r1)
    elif rtype == 'Hipped' or rtype == 'Pyramidal':
        r0 = "%s %s %s" % (o[0]+.5*x, o[1]+width, o[2]+z+h)
        r.append(r0)
        r1 = "%s %s %s" % (o[0]+.5*x, o[1]+y-width, o[2]+z+h)
        r.append(r1)        
    return r


def verticesOverhangs(b, p, h, rtype, ovh, r, width=None):
    """Calculates the vertices of the roof overhangs"""
    #-- The basic information about the building
    o, x, y, z = b
    #-- Roof points
    if r:
        r0, r1 = r
    #-- Overhang lenghts
    ovhx, ovhy = ovh

    overhangs = []
    interior = []

    #-- Overhang points
    if rtype == 'Gabled':

        if ovhx > 0:
            fx = (.5*x) / ovhx
            ovhz = h / fx
        else:
            ovhz = 0

        overhangs.append("")
        overhangs[0] += r0
        overhangs[0] += " %s %s %s" % (o[0]+.5*x, o[1]-ovhy, o[2]+z+h)
        overhangs[0] += " %s %s %s" % (o[0]+x+ovhx, o[1]-ovhy, o[2]+z-ovhz)
        overhangs[0] += " %s %s %s" % (o[0]+x+ovhx, o[1]+y+ovhy, o[2]+z-ovhz)
        overhangs[0] += " %s %s %s" % (o[0]+.5*x, o[1]+y+ovhy, o[2]+z+h)
        overhangs[0] += " " + r1
        overhangs[0] += " " + p[6]
        overhangs[0] += " " + p[5]
        overhangs[0] += " " + r0
        #-- The above polygon has no interior
        interior.append(None)
        
        overhangs.append("")
        overhangs[1] += r1
        overhangs[1] += " %s %s %s" % (o[0]+.5*x, o[1]+y+ovhy, o[2]+z+h)
        overhangs[1] += " %s %s %s" % (o[0]-ovhx, o[1]+y+ovhy, o[2]+z-ovhz)
        overhangs[1] += " %s %s %s" % (o[0]-ovhx, o[1]-ovhy, o[2]+z-ovhz)
        overhangs[1] += " %s %s %s" % (o[0]+.5*x, o[1]-ovhy, o[2]+z+h)
        overhangs[1] += " " + r0
        overhangs[1] += " " + p[4]
        overhangs[1] += " " + p[7]
        overhangs[1] += " " + r1
        #-- The above polygon has no interior
        interior.append(None)

        eaves = o[2]+z-ovhz

    elif rtype == 'Shed':

        if ovhx > 0:
            fx = x / ovhx
            ovhz = h / fx
        else:
            ovhz = 0

        overhangs.append("")
        overhangs[0] += "%s %s %s" % (o[0]-ovhx, o[1]-ovhy, o[2]+z+h+ovhz)
        overhangs[0] += " %s %s %s" % (o[0]+x+ovhx, o[1]-ovhy, o[2]+z-ovhz)
        overhangs[0] += " %s %s %s" % (o[0]+x+ovhx, o[1]+y+ovhy, o[2]+z-ovhz)
        overhangs[0] += " %s %s %s" % (o[0]-ovhx, o[1]+y+ovhy, o[2]+z+h+ovhz)
        overhangs[0] += " %s %s %s" % (o[0]-ovhx, o[1]-ovhy, o[2]+z+h+ovhz)

        interior.append("")
        interior[0] += r0
        interior[0] += " " + r1
        interior[0] += " " + p[6]
        interior[0] += " " + p[5]
        interior[0] += " " + r0

        eaves = o[2]+z-ovhz

    elif rtype == 'Hipped' or rtype == 'Pyramidal':

        if ovhx > 0:
            fx = (.5*x) / ovhx
            ovhz = h / fx
            
            fy = h / ovhz
            ovhy = width / fy

        else:
            ovhy = 0
            ovhz = 0

        overhangs.append("")
        overhangs[0] += "%s %s %s" % (o[0]-ovhx, o[1]-ovhy, o[2]+z-ovhz)
        overhangs[0] += " %s %s %s" % (o[0]+x+ovhx, o[1]-ovhy, o[2]+z-ovhz)
        overhangs[0] += " " + p[5]
        overhangs[0] += " " + p[4]
        overhangs[0] += " %s %s %s" % (o[0]-ovhx, o[1]-ovhy, o[2]+z-ovhz)
        interior.append(None)

        overhangs.append("")
        overhangs[1] += "%s %s %s" % (o[0]+x+ovhx, o[1]-ovhy, o[2]+z-ovhz)
        overhangs[1] += " %s %s %s" % (o[0]+x+ovhx, o[1]+y+ovhy, o[2]+z-ovhz)
        overhangs[1] += " " + p[6]
        overhangs[1] += " " + p[5]
        overhangs[1] += " %s %s %s" % (o[0]+x+ovhx, o[1]-ovhy, o[2]+z-ovhz)
        interior.append(None)

        overhangs.append("")
        overhangs[2] += "%s %s %s" % (o[0]-ovhx, o[1]+y+ovhy, o[2]+z-ovhz)
        overhangs[2] += " " + p[7]
        overhangs[2] += " " + p[6]
        overhangs[2] += " %s %s %s" % (o[0]+x+ovhx, o[1]+y+ovhy, o[2]+z-ovhz)
        overhangs[2] += " %s %s %s" % (o[0]-ovhx, o[1]+y+ovhy, o[2]+z-ovhz)
        interior.append(None)

        overhangs.append("")
        overhangs[3] += "%s %s %s" % (o[0]-ovhx, o[1]-ovhy, o[2]+z-ovhz)
        overhangs[3] += " " + p[4]
        overhangs[3] += " " + p[7]
        overhangs[3] += " %s %s %s" % (o[0]-ovhx, o[1]+y+ovhy, o[2]+z-ovhz)
        overhangs[3] += " %s %s %s" % (o[0]-ovhx, o[1]-ovhy, o[2]+z-ovhz)
        interior.append(None)

        eaves = o[2]+z-ovhz
    
    elif rtype == 'Flat':

        overhangs.append("")
        overhangs[0] += "%s %s %s" % (o[0]-ovhx,o[1]-ovhy,o[2]+z)
        overhangs[0] += " %s %s %s" % (o[0]+x+ovhx,o[1]-ovhy,o[2]+z)
        overhangs[0] += " %s %s %s" % (o[0]+x+ovhx,o[1]+y+ovhy,o[2]+z)
        overhangs[0] += " %s %s %s" % (o[0]-ovhx,o[1]+y+ovhy,o[2]+z)
        overhangs[0] += " %s %s %s" % (o[0]-ovhx,o[1]-ovhy,o[2]+z)

        interior.append("")
        interior[0] += p[4]
        interior[0] += " " + p[7]
        interior[0] += " " + p[6]
        interior[0] += " " + p[5]
        interior[0] += " " + p[4]
        eaves = o[2]+z

    ovhy_recalculated = ovhy

    #-- Overhang points
    return overhangs, interior, eaves, ovhy_recalculated

def wallOpeningOrganiser(openings):
    """Divide the openings per wall."""
    if openings:
        holes = [[], [], [], []]
        opns = [[], [], [], []]
        for i in range(0,4):
            opns[i].append([])
            opns[i].append([])
        door = openings[0]
        if door != '':
            doorwall = int(door['wall'])
            holes[doorwall].append(door['ring'])
            opns[doorwall][0] = door

        for o in openings[1]:
            try:
                windowwall = int(o['wall'])
            except:
                windowwall = int(o['side'])
            holes[windowwall].append(o['ring'])
            opns[windowwall][1].append(o)

    else:
        holes = None
        opns = None

    return holes, opns


def GMLPointList(point):
    """Translates the list of coordinates of one point to a string representation (GML)."""
    x = point[0]
    y = point[1]
    z = point[2]
    return "%s %s %s" % (x, y, z)


def multiGMLPointList(points):
    """Translates the list of multiple points to a string representation (GML)."""
    l = ""
    for t in points:
        if len(l) > 0:
            l += " "
        l += GMLPointList(t)
    return l


def GMLstring2points(pointstring):
    """Converts the list of points in string (GML) to a list."""
    listPoints = []
    #-- List of coordinates
    coords = pointstring.split()
    #-- Store the coordinate tuple
    assert(len(coords) % 3 == 0)
    for i in range(0, len(coords), 3):
        listPoints.append([coords[i], coords[i+1], coords[i+2]])
    return listPoints


def GMLreverser(pointlist):
    """Reverses the order of the points, i.e. the normal of the ring."""
    revlist = pointlist[::-1]
    return revlist


def GMLreversedRing(r):
    """Reverses a ring."""
    gmllist= GMLstring2points(r)
    revgmllist= GMLreverser(gmllist)
    revring = multiGMLPointList(revgmllist)
    return revring


def dormerVertices(dormers, p, h, rtype, oList, width):
    """Computes the vertices of a dormer."""
    [o, x, y, z] = oList
    dList = []
    dListGML = []
    for drm in dormers:
        d = [[], [], [], [], [], []]
        dGML = [[], [], [], [], [], []]
        if rtype == 'Gabled':
            xperimiter = (float(drm['origin'][1]) * x * 0.5) / h
            xperimiter2 = (float(drm['size'][1]) * x * 0.5) / h + xperimiter
            if drm['side'] == 1:
                d[1] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]), p[5][2] + drm['origin'][1]]
                d[2] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]), p[5][2] + drm['origin'][1]]
                d[4] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]), p[5][2] + drm['origin'][1] + float(drm['size'][1])]
                d[5] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]), p[5][2] + drm['origin'][1] + float(drm['size'][1])]
                d[0] = [p[1][0]-xperimiter2, p[1][1] + float(drm['origin'][0]), p[5][2] + drm['origin'][1] + float(drm['size'][1])]
                d[3] = [p[1][0]-xperimiter2, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]), p[5][2] + drm['origin'][1] + float(drm['size'][1])]
            elif drm['side'] == 3:
                d[1] = [p[4][0]+xperimiter, p[7][1] - float(drm['origin'][0]), p[5][2] + drm['origin'][1]]
                d[2] = [p[4][0]+xperimiter, p[7][1] - float(drm['origin'][0]) - float(drm['size'][0]), p[5][2] + drm['origin'][1]]
                d[4] = [p[4][0]+xperimiter, p[7][1] - float(drm['origin'][0]), p[5][2] + drm['origin'][1] + float(drm['size'][1])]
                d[5] = [p[4][0]+xperimiter, p[7][1] - float(drm['origin'][0]) - float(drm['size'][0]), p[5][2] + drm['origin'][1] + float(drm['size'][1])]
                d[0] = [p[4][0]+xperimiter2, p[7][1] - float(drm['origin'][0]), p[5][2] + drm['origin'][1] + float(drm['size'][1])]
                d[3] = [p[4][0]+xperimiter2, p[7][1] - float(drm['origin'][0]) - float(drm['size'][0]), p[5][2] + drm['origin'][1] + float(drm['size'][1])]
        
        elif rtype == 'Shed':
            xperimiter = (float(drm['origin'][1]) * x * 1.0) / h
            xperimiter2 = (float(drm['size'][1]) * x * 1.0) / h + xperimiter            
            if drm['side'] == 1:
                d[1] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]), p[5][2] + drm['origin'][1]]
                d[2] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]), p[5][2] + drm['origin'][1]]
                d[4] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]), p[5][2] + drm['origin'][1] + float(drm['size'][1])]
                d[5] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]), p[5][2] + drm['origin'][1] + float(drm['size'][1])]
                d[0] = [p[1][0]-xperimiter2, p[1][1] + float(drm['origin'][0]), p[5][2] + drm['origin'][1] + float(drm['size'][1])]
                d[3] = [p[1][0]-xperimiter2, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]), p[5][2] + drm['origin'][1] + float(drm['size'][1])]
       
        elif rtype == 'Hipped' or rtype == 'Pyramidal':
            xperimiter = (float(drm['origin'][1]) * x * 0.5) / h
            xperimiter2 = (float(drm['size'][1]) * x * 0.5) / h + xperimiter
            yperimiter = (float(drm['origin'][1]) * width) / h
            yperimiter2 = (float(drm['size'][1]) * width) / h + yperimiter
            if drm['side'] == 1:
                d[1] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]), p[5][2] + drm['origin'][1]]
                d[2] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]), p[5][2] + drm['origin'][1]]
                d[4] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]), p[5][2] + drm['origin'][1] + float(drm['size'][1])]
                d[5] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]), p[5][2] + drm['origin'][1] + float(drm['size'][1])]
                d[0] = [p[1][0]-xperimiter2, p[1][1] + float(drm['origin'][0]), p[5][2] + drm['origin'][1] + float(drm['size'][1])]
                d[3] = [p[1][0]-xperimiter2, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]), p[5][2] + drm['origin'][1] + float(drm['size'][1])]
            elif drm['side'] == 3:
                d[1] = [p[4][0]+xperimiter, p[7][1] - float(drm['origin'][0]), p[5][2] + drm['origin'][1]]
                d[2] = [p[4][0]+xperimiter, p[7][1] - float(drm['origin'][0]) - float(drm['size'][0]), p[5][2] + drm['origin'][1]]
                d[4] = [p[4][0]+xperimiter, p[7][1] - float(drm['origin'][0]), p[5][2] + drm['origin'][1] + float(drm['size'][1])]
                d[5] = [p[4][0]+xperimiter, p[7][1] - float(drm['origin'][0]) - float(drm['size'][0]), p[5][2] + drm['origin'][1] + float(drm['size'][1])]
                d[0] = [p[4][0]+xperimiter2, p[7][1] - float(drm['origin'][0]), p[5][2] + drm['origin'][1] + float(drm['size'][1])]
                d[3] = [p[4][0]+xperimiter2, p[7][1] - float(drm['origin'][0]) - float(drm['size'][0]), p[5][2] + drm['origin'][1] + float(drm['size'][1])]
            elif drm['side'] == 0:
                d[1] = [p[4][0]+float(drm['origin'][0]), p[4][1] + yperimiter, p[5][2] + drm['origin'][1]]
                d[2] = [p[4][0]+float(drm['origin'][0])+float(drm['size'][0]), p[4][1]  + yperimiter, p[5][2] + drm['origin'][1]]
                d[4] = [p[4][0]+float(drm['origin'][0]), p[4][1]  + yperimiter, p[5][2] + drm['origin'][1] + float(drm['size'][1])]
                d[5] = [p[4][0]+float(drm['origin'][0])+float(drm['size'][0]), p[4][1]  + yperimiter, p[5][2] + drm['origin'][1] + float(drm['size'][1])]
                d[0] = [p[4][0]+float(drm['origin'][0]), p[4][1]  + yperimiter2, p[5][2] + drm['origin'][1] + float(drm['size'][1])]
                d[3] = [p[4][0]+float(drm['origin'][0])+float(drm['size'][0]), p[4][1]  + yperimiter2, p[5][2] + drm['origin'][1] + float(drm['size'][1])]
            elif drm['side'] == 2:
                d[1] = [p[6][0]-float(drm['origin'][0]), p[6][1] - yperimiter, p[5][2] + drm['origin'][1]]
                d[2] = [p[6][0]-float(drm['origin'][0])-float(drm['size'][0]), p[6][1]  - yperimiter, p[5][2] + drm['origin'][1]]
                d[4] = [p[6][0]-float(drm['origin'][0]), p[6][1] - yperimiter, p[5][2] + drm['origin'][1] + float(drm['size'][1])]
                d[5] = [p[6][0]-float(drm['origin'][0])-float(drm['size'][0]), p[6][1]  - yperimiter, p[5][2] + drm['origin'][1] + float(drm['size'][1])]
                d[0] = [p[6][0]-float(drm['origin'][0]), p[6][1] - yperimiter2, p[5][2] + drm['origin'][1] + float(drm['size'][1])]
                d[3] = [p[6][0]-float(drm['origin'][0])-float(drm['size'][0]), p[6][1] - yperimiter2, p[5][2] + drm['origin'][1] + float(drm['size'][1])]                

        elif rtype == 'Flat':
            #-- Valid only for roof windows
            xperimiter = float(drm['origin'][1])
            xperimiter2 = float(drm['size'][1]) + xperimiter 
            if drm['side'] == 1:
                d[1] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]), p[5][2]]
                d[2] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]), p[5][2]]
                d[4] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]), p[5][2] + drm['origin'][1] + float(drm['size'][1])]
                d[5] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]), p[5][2] + drm['origin'][1] + float(drm['size'][1])]
                d[0] = [p[1][0]-xperimiter2, p[1][1] + float(drm['origin'][0]), p[5][2]]
                d[3] = [p[1][0]-xperimiter2, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]), p[5][2]]

        if d != [[], [], [], [], [], []]:
            for i in range(0, 6):
                #for j in range(0, 3):
                #    d[i][j] = round(d[i][j], 2)
                dGML[i] = GMLPointList(d[i])
        dList.append(d)
        dListGML.append(dGML)

    return dList, dListGML

def interiordormerVertices(dormers, p, h, rtype, oList, width, wallThickness, rWth, dormerTickness, topThickness, rWth2=None):
    """Computes the vertices of a dormer."""
    [o, x, y, z] = oList
    dList = []
    dListGML = []
    for drm in dormers:
        d = [[], [], [], [], [], []]
        dGML = [[], [], [], [], [], []]
        if rtype == 'Gabled':
            xperimiter = (float(drm['origin'][1]) * x * 0.5) / h
            xperimiter2 = (float(drm['size'][1]) * x * 0.5) / h + xperimiter
            intxper = (xperimiter + dormerTickness) - rWth
            dper2 = ((drm['origin'][1] + float(drm['size'][1]) - dormerTickness) * x * 0.5) / h + rWth
            hper1 = intxper * h / (.5 * x)
            if drm['side'] == 1:
                d[1] = [p[1][0]-xperimiter - dormerTickness, p[1][1] + float(drm['origin'][0]) + dormerTickness, p[5][2] + hper1]
                d[2] = [p[1][0]-xperimiter - dormerTickness, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]) - dormerTickness, p[5][2] + hper1]
                d[4] = [p[1][0]-xperimiter - dormerTickness, p[1][1] + float(drm['origin'][0]) + dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]
                d[5] = [p[1][0]-xperimiter - dormerTickness, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]) - dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]
                d[0] = [p[1][0]- dper2, p[1][1] + float(drm['origin'][0]) + dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]
                d[3] = [p[1][0]- dper2, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]) - dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]
            elif drm['side'] == 3:
                # d[1] = [p[1][0]+xperimiter + dormerTickness, p[1][1] - float(drm['origin'][0]) - dormerTickness, p[5][2] + hper1]
                # d[2] = [p[1][0]+xperimiter + dormerTickness, p[1][1] - float(drm['origin'][0]) - float(drm['size'][0]) + dormerTickness, p[5][2] + hper1]
                # d[4] = [p[1][0]+xperimiter + dormerTickness, p[1][1] - float(drm['origin'][0]) - dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]
                # d[5] = [p[1][0]+xperimiter + dormerTickness, p[1][1] - float(drm['origin'][0]) - float(drm['size'][0]) + dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]
                # d[0] = [p[1][0]+xperimiter2 + (rWth-dormerTickness), p[1][1] - float(drm['origin'][0]) - dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]
                # d[3] = [p[1][0]+xperimiter2 + (rWth-dormerTickness), p[1][1] - float(drm['origin'][0]) - float(drm['size'][0]) + dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]
 
                d[1] = [p[4][0]+xperimiter + dormerTickness, p[7][1] - float(drm['origin'][0]) - dormerTickness, p[5][2] + hper1]
                d[2] = [p[4][0]+xperimiter + dormerTickness, p[7][1] - float(drm['origin'][0]) - float(drm['size'][0]) + dormerTickness, p[5][2] + hper1]
                d[4] = [p[4][0]+xperimiter + dormerTickness, p[7][1] - float(drm['origin'][0]) - dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]
                d[5] = [p[4][0]+xperimiter + dormerTickness, p[7][1] - float(drm['origin'][0]) - float(drm['size'][0]) + dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]
                d[0] = [p[4][0] + dper2, p[7][1] - float(drm['origin'][0]) - dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]
                d[3] = [p[4][0] + dper2, p[7][1] - float(drm['origin'][0]) - float(drm['size'][0]) + dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]
        
        elif rtype == 'Shed':
            xperimiter = (float(drm['origin'][1]) * x) / h
            xperimiter2 = (float(drm['size'][1]) * x) / h + xperimiter 
            intxper = (xperimiter + dormerTickness) - rWth
            dper2 = ((drm['origin'][1] + float(drm['size'][1]) - dormerTickness) * x) / h + rWth
            hper1 = intxper * h / x
            if drm['side'] == 1:
                # d[1] = [p[1][0]-xperimiter - rWth, p[1][1] + float(drm['origin'][0]) + dormerTickness, p[5][2] + drm['origin'][1]]
                # d[2] = [p[1][0]-xperimiter - rWth, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]) - dormerTickness, p[5][2] + drm['origin'][1]]
                # d[4] = [p[1][0]-xperimiter - rWth, p[1][1] + float(drm['origin'][0]) + dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - topThickness]
                # d[5] = [p[1][0]-xperimiter - rWth, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]) - dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - topThickness]
                # d[0] = [p[1][0]-xperimiter2, p[1][1] + float(drm['origin'][0]) + dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - topThickness]
                # d[3] = [p[1][0]-xperimiter2, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]) - dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - topThickness]
                d[1] = [p[1][0]-xperimiter - dormerTickness, p[1][1] + float(drm['origin'][0]) + dormerTickness, p[5][2] + hper1]
                d[2] = [p[1][0]-xperimiter - dormerTickness, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]) - dormerTickness, p[5][2] + hper1]
                d[4] = [p[1][0]-xperimiter - dormerTickness, p[1][1] + float(drm['origin'][0]) + dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]
                d[5] = [p[1][0]-xperimiter - dormerTickness, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]) - dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]
                d[0] = [p[1][0] - dper2, p[1][1] + float(drm['origin'][0]) + dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]
                d[3] = [p[1][0] - dper2, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]) - dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]

        elif rtype == 'Hipped' or rtype == 'Pyramidal':
            xperimiter = (float(drm['origin'][1]) * x * 0.5) / h
            xperimiter2 = (float(drm['size'][1]) * x * 0.5) / h + xperimiter
            yperimiter = (float(drm['origin'][1]) * width) / h
            yperimiter2 = (float(drm['size'][1]) * width) / h + yperimiter
            intxper = (xperimiter + dormerTickness) - rWth
            dper2 = ((drm['origin'][1] + float(drm['size'][1]) - dormerTickness) * x * 0.5) / h + rWth
            hper1 = intxper * h / (.5 * x)

            intyper = (yperimiter + dormerTickness) - rWth2
            dper2_2 = ((drm['origin'][1] + float(drm['size'][1]) - dormerTickness) * width) / h + rWth2
            hper2 = (intyper) * h / width
            if drm['side'] == 1:
                # d[1] = [p[1][0]-xperimiter - rWth, p[1][1] + float(drm['origin'][0]) + dormerTickness, p[5][2] + drm['origin'][1]]
                # d[2] = [p[1][0]-xperimiter - rWth, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]) - dormerTickness, p[5][2] + drm['origin'][1]]
                # d[4] = [p[1][0]-xperimiter - rWth, p[1][1] + float(drm['origin'][0]) + dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - topThickness]
                # d[5] = [p[1][0]-xperimiter - rWth, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]) - dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - topThickness]
                # d[0] = [p[1][0]-xperimiter2, p[1][1] + float(drm['origin'][0]) + dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - topThickness]
                # d[3] = [p[1][0]-xperimiter2, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]) - dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - topThickness]
                d[1] = [p[1][0]-xperimiter - dormerTickness, p[1][1] + float(drm['origin'][0]) + dormerTickness, p[5][2] + hper1]
                d[2] = [p[1][0]-xperimiter - dormerTickness, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]) - dormerTickness, p[5][2] + hper1]
                d[4] = [p[1][0]-xperimiter - dormerTickness, p[1][1] + float(drm['origin'][0]) + dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]
                d[5] = [p[1][0]-xperimiter - dormerTickness, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]) - dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]
                d[0] = [p[1][0] - dper2, p[1][1] + float(drm['origin'][0]) + dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]
                d[3] = [p[1][0] - dper2, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]) - dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]
            elif drm['side'] == 3:
                d[1] = [p[4][0]+xperimiter + dormerTickness, p[7][1] - float(drm['origin'][0]) - dormerTickness, p[5][2] + hper1]
                d[2] = [p[4][0]+xperimiter + dormerTickness, p[7][1] - float(drm['origin'][0]) - float(drm['size'][0]) + dormerTickness, p[5][2] + hper1]
                d[4] = [p[4][0]+xperimiter + dormerTickness, p[7][1] - float(drm['origin'][0]) - dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]
                d[5] = [p[4][0]+xperimiter + dormerTickness, p[7][1] - float(drm['origin'][0]) - float(drm['size'][0]) + dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]
                d[0] = [p[4][0]+ dper2, p[7][1] - float(drm['origin'][0]) - dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]
                d[3] = [p[4][0]+ dper2, p[7][1] - float(drm['origin'][0]) - float(drm['size'][0]) + dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]
            elif drm['side'] == 0:
                d[1] = [p[4][0]+float(drm['origin'][0]) + dormerTickness, p[4][1] + yperimiter + dormerTickness, p[5][2] + hper2]
                d[2] = [p[4][0]+float(drm['origin'][0])+float(drm['size'][0]) - dormerTickness, p[4][1] + yperimiter + dormerTickness, p[5][2] + hper2]
                d[4] = [p[4][0]+float(drm['origin'][0]) + dormerTickness, p[4][1]  + yperimiter + dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]
                d[5] = [p[4][0]+float(drm['origin'][0])+float(drm['size'][0]) - dormerTickness, p[4][1] + yperimiter + dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]
                d[0] = [p[4][0]+float(drm['origin'][0]) + dormerTickness, p[4][1] + dper2_2, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]
                d[3] = [p[4][0]+float(drm['origin'][0])+float(drm['size'][0]) - dormerTickness, p[4][1] + dper2_2, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]
            elif drm['side'] == 2:
                d[1] = [p[6][0]-float(drm['origin'][0]) - dormerTickness, p[6][1] - yperimiter - dormerTickness, p[5][2] + hper2]
                d[2] = [p[6][0]-float(drm['origin'][0])-float(drm['size'][0]) + dormerTickness, p[6][1]  - yperimiter - dormerTickness, p[5][2] + hper2]
                d[4] = [p[6][0]-float(drm['origin'][0]) - dormerTickness, p[6][1] - yperimiter - dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]
                d[5] = [p[6][0]-float(drm['origin'][0])-float(drm['size'][0]) + dormerTickness, p[6][1]  - yperimiter - dormerTickness, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]
                d[0] = [p[6][0]-float(drm['origin'][0]) - dormerTickness, p[6][1] - dper2_2, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]
                d[3] = [p[6][0]-float(drm['origin'][0])-float(drm['size'][0]) + dormerTickness, p[6][1] - dper2_2, p[5][2] + drm['origin'][1] + float(drm['size'][1]) - dormerTickness]              

        if d != [[], [], [], [], [], []]:
            for i in range(0, 6):
                #for j in range(0, 3):
                #    d[i][j] = round(d[i][j], 2)
                dGML[i] = GMLPointList(d[i])
        dList.append(d)
        dListGML.append(dGML)

    return dList, dListGML



def chimneyVertices(chimneys, p, h, rtype, oList, width):
    """
    Computes the vertices of a chimney.
    The origin in chimneys is different than the one in dormers, hence a separate function.
    """
    [o, x, y, z] = oList
    dList = []
    dListGML = []
    for drm in chimneys:
        d = [[], [], [], [], [], [], [], []]
        dGML = [[], [], [], [], [], [], [], []]
        chHeight = float(drm['size'][2])
        if rtype == 'Gabled':
            #xperimiter = (float(drm['origin'][1]) * x * 0.5) / h
            #xperimiter2 = (float(drm['size'][1]) * x * 0.5) / h + xperimiter
            xperimiter = float(drm['origin'][1])
            xperimiter2 = float(drm['size'][1]) + xperimiter
            zperimiter1 = (xperimiter * h) / (x*.5)
            zperimiter2 = (xperimiter2 * h) / (x*.5)
            if drm['side'] == 1:
                d[1] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]), p[5][2] + zperimiter1]
                d[2] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]), p[5][2] + zperimiter1]
                d[4] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]), p[5][2] + zperimiter2 + chHeight]
                d[5] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]), p[5][2] + zperimiter2 + chHeight]
                d[0] = [p[1][0]-xperimiter2, p[1][1] + float(drm['origin'][0]), p[5][2] + zperimiter2]
                d[3] = [p[1][0]-xperimiter2, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]), p[5][2] + zperimiter2]
                d[7] = [p[1][0]-xperimiter2, p[1][1] + float(drm['origin'][0]), p[5][2] + zperimiter2 + chHeight]
                d[6] = [p[1][0]-xperimiter2, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]), p[5][2] + zperimiter2 + chHeight]
            elif drm['side'] == 3:
                d[1] = [p[4][0]+xperimiter, p[7][1] - float(drm['origin'][0]), p[5][2] + zperimiter1]
                d[2] = [p[4][0]+xperimiter, p[7][1] - float(drm['origin'][0]) - float(drm['size'][0]), p[5][2] + zperimiter1]
                d[4] = [p[4][0]+xperimiter, p[7][1] - float(drm['origin'][0]), p[5][2] + zperimiter2 + chHeight]
                d[5] = [p[4][0]+xperimiter, p[7][1] - float(drm['origin'][0]) - float(drm['size'][0]), p[5][2] + zperimiter2 + chHeight]
                d[0] = [p[4][0]+xperimiter2, p[7][1] - float(drm['origin'][0]), p[5][2] + zperimiter2]
                d[3] = [p[4][0]+xperimiter2, p[7][1] - float(drm['origin'][0]) - float(drm['size'][0]), p[5][2] + zperimiter2]
                d[7] = [p[4][0]+xperimiter2, p[7][1] - float(drm['origin'][0]), p[5][2] + zperimiter2 + chHeight]
                d[6] = [p[4][0]+xperimiter2, p[7][1] - float(drm['origin'][0]) - float(drm['size'][0]), p[5][2] + zperimiter2 + chHeight]

        elif rtype == 'Shed':
            #xperimiter = (float(drm['origin'][1]) * x * 1.0) / h
            xperimiter = float(drm['origin'][1]) 
            #xperimiter2 = (float(drm['size'][1]) * x * 1.0) / h + xperimiter
            xperimiter2 = float(drm['size'][1]) + xperimiter
            zperimiter1 = (xperimiter * h) / x
            zperimiter2 = (xperimiter2 * h) / x
            if drm['side'] == 1:
                d[1] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]), p[5][2] + zperimiter1]
                d[2] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]), p[5][2] + zperimiter1]
                d[4] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]), p[5][2] + zperimiter2 + chHeight]
                d[5] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]), p[5][2] + zperimiter2 + chHeight]
                d[0] = [p[1][0]-xperimiter2, p[1][1] + float(drm['origin'][0]), p[5][2] + zperimiter2]
                d[3] = [p[1][0]-xperimiter2, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]), p[5][2] + zperimiter2]
                d[7] = [p[1][0]-xperimiter2, p[1][1] + float(drm['origin'][0]), p[5][2] + zperimiter2 + chHeight]
                d[6] = [p[1][0]-xperimiter2, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]), p[5][2] + zperimiter2 + chHeight]
       
        elif rtype == 'Hipped' or rtype == 'Pyramidal':

            xperimiter = float(drm['origin'][1])
            xperimiter2 = float(drm['size'][1]) + xperimiter
            yperimiter = (float(drm['origin'][1]) * width) / h
            yperimiter2 = (float(drm['size'][1]) * width) / h + yperimiter
            zperimiter1 = (xperimiter * h) / (x*.5)
            zperimiter2 = (xperimiter2 * h) / (x*.5)

            if drm['side'] == 1:
                d[1] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]), p[5][2] + zperimiter1]
                d[2] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]), p[5][2] + zperimiter1]
                d[4] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]), p[5][2] + zperimiter2 + chHeight]
                d[5] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]), p[5][2] + zperimiter2 + chHeight]
                d[0] = [p[1][0]-xperimiter2, p[1][1] + float(drm['origin'][0]), p[5][2] + zperimiter2]
                d[3] = [p[1][0]-xperimiter2, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]), p[5][2] + zperimiter2]
                d[7] = [p[1][0]-xperimiter2, p[1][1] + float(drm['origin'][0]), p[5][2] + zperimiter2 + chHeight]
                d[6] = [p[1][0]-xperimiter2, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]), p[5][2] + zperimiter2 + chHeight]
            elif drm['side'] == 3:
                d[1] = [p[4][0]+xperimiter, p[7][1] - float(drm['origin'][0]), p[5][2] + zperimiter1]
                d[2] = [p[4][0]+xperimiter, p[7][1] - float(drm['origin'][0]) - float(drm['size'][0]), p[5][2] + zperimiter1]
                d[4] = [p[4][0]+xperimiter, p[7][1] - float(drm['origin'][0]), p[5][2] + zperimiter2 + chHeight]
                d[5] = [p[4][0]+xperimiter, p[7][1] - float(drm['origin'][0]) - float(drm['size'][0]), p[5][2] + zperimiter2 + chHeight]
                d[0] = [p[4][0]+xperimiter2, p[7][1] - float(drm['origin'][0]), p[5][2] + zperimiter2]
                d[3] = [p[4][0]+xperimiter2, p[7][1] - float(drm['origin'][0]) - float(drm['size'][0]), p[5][2] + zperimiter2]
                d[7] = [p[4][0]+xperimiter2, p[7][1] - float(drm['origin'][0]), p[5][2] + zperimiter2 + chHeight]
                d[6] = [p[4][0]+xperimiter2, p[7][1] - float(drm['origin'][0]) - float(drm['size'][0]), p[5][2] + zperimiter2 + chHeight]

        elif rtype == 'Flat':
            #-- Not valid for dormers
            xperimiter = float(drm['origin'][1])
            xperimiter2 = float(drm['size'][1]) + xperimiter    
            if drm['side'] == 1:
                d[1] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]), p[5][2]]
                d[2] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]), p[5][2]]
                d[4] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]), p[5][2] + chHeight]
                d[5] = [p[1][0]-xperimiter, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]), p[5][2] + chHeight]
                d[0] = [p[1][0]-xperimiter2, p[1][1] + float(drm['origin'][0]), p[5][2]]
                d[3] = [p[1][0]-xperimiter2, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]), p[5][2]]
                d[7] = [p[1][0]-xperimiter2, p[1][1] + float(drm['origin'][0]), p[5][2] + chHeight]
                d[6] = [p[1][0]-xperimiter2, p[1][1] + float(drm['origin'][0]) + float(drm['size'][0]), p[5][2] + chHeight]

        if d != [[], [], [], [], [], []]:
            for i in range(0, 8):
                #for j in range(0, 3):
                #    d[i][j] = round(d[i][j], 2)
                dGML[i] = GMLPointList(d[i])
        dList.append(d)
        dListGML.append(dGML)

    return dList, dListGML

def adjustRoofFeatures(roofType, eaves, old_origin, overhang_x, overhang_y, side):
    """This function adjusts the location of the features of the roof for models of different geometric references."""
    old_x = old_origin[0]
    old_y = old_origin[1]

    if roofType == 'Gabled' or roofType == 'Shed' or roofType == 'Hipped' or roofType == 'Pyramidal':
        if side == 1 or side == 3:
            adjusted_x = old_x + overhang_y
            adjusted_y = old_y + eaves
        elif side == 0 or side == 2:
            adjusted_x = old_x + overhang_x
            adjusted_y = old_y + eaves
    elif roofType == 'Flat':
        adjusted_x = old_x + overhang_y
        adjusted_y = old_y + overhang_x
        #xperimiter = float(drm['origin'][1])

    return [adjusted_x, adjusted_y]

def gabledRoof(XMLelement, p, r, override_wall=None, semantics=None, openings=None, roofopenings=None, rfWindows=None, embrasure=None, pList=None):
    """Constructs a building with a gabled roof."""
    #-- Roof Surface
    roof0 = "%s %s %s %s %s" % (r[0], r[1], p[7], p[4], r[0])
    roof1 = "%s %s %s %s %s" % (r[1], r[0], p[5], p[6], r[1])

    #-- Wall Surface
    face0 = "%s %s %s %s %s %s" % (p[4], p[0], p[1], p[5], r[0], p[4])
    if override_wall:
        face1 = override_wall['wall']
    else:
        face1 = "%s %s %s %s %s" % (p[5], p[1], p[2], p[6], p[5])
    face2 = "%s %s %s %s %s %s" % (p[6], p[2], p[3], p[7], r[1], p[6])
    face3 = "%s %s %s %s %s" % (p[7], p[3], p[0], p[4], p[7])

    if openings:
        holes, opns = wallOpeningOrganiser(openings)
    else:
        holes = None
        opns = None

    if embrasure and openings:
        embO = embrasuresGeometry(openings, pList, embrasure)

    if semantics:
        if roofopenings:
            if rfWindows:
                multiSurface2(XMLelement, roof0, "RoofSurface", roofopenings[3], 3, rfWindows[3])
                multiSurface2(XMLelement, roof1, "RoofSurface", roofopenings[1], 3, rfWindows[1])
            else:
                multiSurface(XMLelement, roof0, "RoofSurface", roofopenings[3], 3)
                multiSurface(XMLelement, roof1, "RoofSurface", roofopenings[1], 3)
        else:
            multiSurface(XMLelement, roof0, "RoofSurface")
            multiSurface(XMLelement, roof1, "RoofSurface")
        if openings:
            if embrasure:
                multiSurfaceWithEmbrasure(XMLelement, face0, "WallSurface", holes[0], 3, embO[0])
            else:
                multiSurface(XMLelement, face0, "WallSurface", holes[0], 3, opns[0])
        else:
            multiSurface(XMLelement, face0, "WallSurface", None)
        if openings:
            if embrasure:
                multiSurfaceWithEmbrasure(XMLelement, face1, "WallSurface", holes[1], 3, embO[1])
            else:
                multiSurface(XMLelement, face1, "WallSurface", holes[1], 3, opns[1])
        else:    
            multiSurface(XMLelement, face1, "WallSurface", None)
        if openings:
            if embrasure:
                multiSurfaceWithEmbrasure(XMLelement, face2, "WallSurface", holes[2], 3, embO[2])
            else:
                multiSurface(XMLelement, face2, "WallSurface", holes[2], 3, opns[2])
        else:    
            multiSurface(XMLelement, face2, "WallSurface", None)
        if openings:
            if embrasure:
                multiSurfaceWithEmbrasure(XMLelement, face3, "WallSurface", holes[3], 3, embO[3])
            else:
                multiSurface(XMLelement, face3, "WallSurface", holes[3], 3, opns[3])
        else:    
            multiSurface(XMLelement, face3, "WallSurface", None)

        #-- Building part
        for fc in override_wall['rest']:
            multiSurface(XMLelement, fc, "WallSurface", None)
        for fc in override_wall['roof']:
            multiSurface(XMLelement, fc, "RoofSurface", None)
        for fc in override_wall['outerfloor']:
            multiSurface(XMLelement, fc, "OuterFloorSurface", None)

    else:
        if roofopenings is not None:
            addsurface(False, XMLelement, roof0, roofopenings[3])
            addsurface(False, XMLelement, roof1, roofopenings[1])
        else:
            addsurface(False, XMLelement, roof0)
            addsurface(False, XMLelement, roof1)
        if holes is not None:
            if embrasure:
                addSurfaceWithEmbrasure(False, XMLelement, face0, holes[0], embO[0])
                addSurfaceWithEmbrasure(False, XMLelement, face1, holes[1], embO[1])
                addSurfaceWithEmbrasure(False, XMLelement, face2, holes[2], embO[2])
                addSurfaceWithEmbrasure(False, XMLelement, face3, holes[3], embO[3])
            else:
                addsurface(False, XMLelement, face0)
                addsurface(False, XMLelement, face1)
                addsurface(False, XMLelement, face2)
                addsurface(False, XMLelement, face3)

        else:
            addsurface(False, XMLelement, face0)
            addsurface(False, XMLelement, face1)
            addsurface(False, XMLelement, face2)
            addsurface(False, XMLelement, face3)

        for fc in override_wall['rest']:
            addsurface(False, XMLelement, fc)
        for fc in override_wall['roof']:
            addsurface(False, XMLelement, fc)
        for fc in override_wall['outerfloor']:
            addsurface(False, XMLelement, fc)


def shedRoof(XMLelement, p, r, override_wall=None, semantics=None, openings=None, roofopenings=None, rfWindows=None, embrasure=None, pList=None):
    """Constructs a building with a shed roof."""
    #-- Roof Surface
    roof1 = "%s %s %s %s %s" % (r[1], r[0], p[5], p[6], r[1])

    #-- Wall Surface
    face0 = "%s %s %s %s %s" % (r[0], p[0], p[1], p[5], r[0])
    if override_wall:
        face1 = override_wall['wall']
    else:
        face1 = "%s %s %s %s %s" % (p[5], p[1], p[2], p[6], p[5])
    face2 = "%s %s %s %s %s" % (p[6], p[2], p[3], r[1], p[6])
    face3 = "%s %s %s %s %s" % (r[1], p[3], p[0], r[0], r[1])

    if openings:
        holes, opns = wallOpeningOrganiser(openings)
    else:
        holes = None
        opns = None

    if embrasure and openings:
        embO = embrasuresGeometry(openings, pList, embrasure)


    if semantics:
        if roofopenings:
            if rfWindows:
                multiSurface2(XMLelement, roof1, "RoofSurface", roofopenings[1], 3, rfWindows[1])
            else:
                multiSurface(XMLelement, roof1, "RoofSurface", roofopenings[1], 3)
        else:
            multiSurface(XMLelement, roof1, "RoofSurface")
        if openings:
            if embrasure:
                multiSurfaceWithEmbrasure(XMLelement, face0, "WallSurface", holes[0], 3, embO[0])
            else:
                multiSurface(XMLelement, face0, "WallSurface", holes[0], 3, opns[0])
        else:
            multiSurface(XMLelement, face0, "WallSurface", None)
        if openings:
            if embrasure:
                multiSurfaceWithEmbrasure(XMLelement, face1, "WallSurface", holes[1], 3, embO[1])
            else:
                multiSurface(XMLelement, face1, "WallSurface", holes[1], 3, opns[1])
        else:    
            multiSurface(XMLelement, face1, "WallSurface", None)
        if openings:
            if embrasure:
                multiSurfaceWithEmbrasure(XMLelement, face2, "WallSurface", holes[2], 3, embO[2])
            else:
                multiSurface(XMLelement, face2, "WallSurface", holes[2], 3, opns[2])
        else:    
            multiSurface(XMLelement, face2, "WallSurface", None)
        if openings:
            if embrasure:
                multiSurfaceWithEmbrasure(XMLelement, face3, "WallSurface", holes[3], 3, embO[3])
            else:
                multiSurface(XMLelement, face3, "WallSurface", holes[3], 3, opns[3])
        else:    
            multiSurface(XMLelement, face3, "WallSurface", None) 

        #-- Building part
        for fc in override_wall['rest']:
            multiSurface(XMLelement, fc, "WallSurface", None)
        for fc in override_wall['roof']:
            multiSurface(XMLelement, fc, "RoofSurface", None)
        for fc in override_wall['outerfloor']:
            multiSurface(XMLelement, fc, "OuterFloorSurface", None)

    else:
        if roofopenings is not None:
            addsurface(False, XMLelement, roof1, roofopenings[1])
        else:
            addsurface(False, XMLelement, roof1)
        if holes is not None and embrasure:
            addSurfaceWithEmbrasure(False, XMLelement, face0, holes[0], embO[0])
            addSurfaceWithEmbrasure(False, XMLelement, face1, holes[1], embO[1])
            addSurfaceWithEmbrasure(False, XMLelement, face2, holes[2], embO[2])
            addSurfaceWithEmbrasure(False, XMLelement, face3, holes[3], embO[3])            
        else:
            #addsurface(False, XMLelement, roof1)
            addsurface(False, XMLelement, face0)
            addsurface(False, XMLelement, face1)
            addsurface(False, XMLelement, face2)
            addsurface(False, XMLelement, face3)

        for fc in override_wall['rest']:
            addsurface(False, XMLelement, fc)
        for fc in override_wall['roof']:
            addsurface(False, XMLelement, fc)
        for fc in override_wall['outerfloor']:
            addsurface(False, XMLelement, fc)


def hippedRoof(XMLelement, p, r, override_wall=None, semantics=None, openings=None, roofopenings=None, rfWindows=None, embrasure=None, pList=None):
    """Constructs a building with a hipped or pyramidal roof."""
    #-- Roof Surface
    #-- Pyramidal roof has the same point r0 and r1
    if r[0] == r[1]:
        roof0 = "%s %s %s %s" % (r[0], p[7], p[4], r[0])
        roof1 = "%s %s %s %s" % (r[1], p[5], p[6], r[1])    
    else:
        roof0 = "%s %s %s %s %s" % (r[0], r[1], p[7], p[4], r[0])
        roof1 = "%s %s %s %s %s" % (r[1], r[0], p[5], p[6], r[1])
    roofX = "%s %s %s %s" % (r[0], p[4], p[5], r[0])
    roofY = "%s %s %s %s" % (r[1], p[6], p[7], r[1])

    #-- Wall Surface
    face0 = "%s %s %s %s %s" % (p[0], p[1], p[5], p[4], p[0])
    if override_wall:
        face1 = override_wall['wall']
    else:
        face1 = "%s %s %s %s %s" % (p[5], p[1], p[2], p[6], p[5])
    face2 = "%s %s %s %s %s" % (p[2], p[3], p[7], p[6], p[2])
    face3 = "%s %s %s %s %s" % (p[3], p[0], p[4], p[7], p[3])   

    if openings:
        holes, opns = wallOpeningOrganiser(openings)
    else:
        holes = None
        opns = None

    if embrasure and openings:
        embO = embrasuresGeometry(openings, pList, embrasure)  

    if semantics:
        if roofopenings:
            if rfWindows:
                multiSurface2(XMLelement, roof0, "RoofSurface", roofopenings[3], 3, rfWindows[3])
                multiSurface2(XMLelement, roof1, "RoofSurface", roofopenings[1], 3, rfWindows[1])
                multiSurface2(XMLelement, roofX, "RoofSurface", roofopenings[0], 3, rfWindows[0])
                multiSurface2(XMLelement, roofY, "RoofSurface", roofopenings[2], 3, rfWindows[2])
            else:
                multiSurface(XMLelement, roof0, "RoofSurface", roofopenings[3], 3)
                multiSurface(XMLelement, roof1, "RoofSurface", roofopenings[1], 3)
                multiSurface(XMLelement, roofX, "RoofSurface", roofopenings[0], 3)
                multiSurface(XMLelement, roofY, "RoofSurface", roofopenings[2], 3)
        else:
            multiSurface(XMLelement, roof0, "RoofSurface")
            multiSurface(XMLelement, roof1, "RoofSurface")
            multiSurface(XMLelement, roofX, "RoofSurface")
            multiSurface(XMLelement, roofY, "RoofSurface")
        if openings:
            if embrasure:
                multiSurfaceWithEmbrasure(XMLelement, face0, "WallSurface", holes[0], 3, embO[0])
            else:
                multiSurface(XMLelement, face0, "WallSurface", holes[0], 3, opns[0])
        else:
            multiSurface(XMLelement, face0, "WallSurface", None)
        if openings:
            if embrasure:
                multiSurfaceWithEmbrasure(XMLelement, face1, "WallSurface", holes[1], 3, embO[1])
            else:
                multiSurface(XMLelement, face1, "WallSurface", holes[1], 3, opns[1])
        else:    
            multiSurface(XMLelement, face1, "WallSurface", None)
        if openings:
            if embrasure:
                multiSurfaceWithEmbrasure(XMLelement, face2, "WallSurface", holes[2], 3, embO[2])
            else:
                multiSurface(XMLelement, face2, "WallSurface", holes[2], 3, opns[2])
        else:    
            multiSurface(XMLelement, face2, "WallSurface", None)
        if openings:
            if embrasure:
                multiSurfaceWithEmbrasure(XMLelement, face3, "WallSurface", holes[3], 3, embO[3])
            else:
                multiSurface(XMLelement, face3, "WallSurface", holes[3], 3, opns[3])
        else:    
            multiSurface(XMLelement, face3, "WallSurface", None)   

        #-- Building part
        for fc in override_wall['rest']:
            multiSurface(XMLelement, fc, "WallSurface", None)
        for fc in override_wall['roof']:
            multiSurface(XMLelement, fc, "RoofSurface", None)
        for fc in override_wall['outerfloor']:
            multiSurface(XMLelement, fc, "OuterFloorSurface", None)

    else:
        if roofopenings is not None:
            addsurface(False, XMLelement, roof0, roofopenings[3])
            addsurface(False, XMLelement, roof1, roofopenings[1])
            addsurface(False, XMLelement, roofX, roofopenings[0])
            addsurface(False, XMLelement, roofY, roofopenings[2])           
        else:
            addsurface(False, XMLelement, roof0)
            addsurface(False, XMLelement, roof1)
            addsurface(False, XMLelement, roofX)
            addsurface(False, XMLelement, roofY)
        if holes is not None and embrasure:
            addSurfaceWithEmbrasure(False, XMLelement, face0, holes[0], embO[0])
            addSurfaceWithEmbrasure(False, XMLelement, face1, holes[1], embO[1])
            addSurfaceWithEmbrasure(False, XMLelement, face2, holes[2], embO[2])
            addSurfaceWithEmbrasure(False, XMLelement, face3, holes[3], embO[3])            
        else:
            addsurface(False, XMLelement, face0)
            addsurface(False, XMLelement, face1)
            addsurface(False, XMLelement, face2)
            addsurface(False, XMLelement, face3)

        for fc in override_wall['rest']:
            addsurface(False, XMLelement, fc)
        for fc in override_wall['roof']:
            addsurface(False, XMLelement, fc)
        for fc in override_wall['outerfloor']:
            addsurface(False, XMLelement, fc)


def hippedAttic(CompositeSurface, intcoor, p, r, fel, cel, wallThickness, topThickness, atticbottom=False, roofopenings=None):
    """Constructs the interior of the attic of a hipped roof."""
    [Xa, Ya, Xb, Yb] = intcoor
    rA = str(r[0][0]) + ' ' + str(float(r[0][1]) + wallThickness) + ' ' + str(cel)
    rB = str(r[1][0]) + ' ' + str(float(r[1][1]) - wallThickness) + ' ' + str(cel)
    p0F = str(Xa) + ' ' + str(Ya) + ' ' + str(fel)
    p1F = str(Xb) + ' ' + str(Ya) + ' ' + str(fel)
    p2F = str(Xb) + ' ' + str(Yb) + ' ' + str(fel)
    p3F = str(Xa) + ' ' + str(Yb) + ' ' + str(fel)
    S = "%s %s %s %s" % (p0F, p1F, rA, p0F)
    E = "%s %s %s %s %s" % (p1F, p2F, rB, rA, p1F)
    N = "%s %s %s %s" % (p2F, p3F, rB, p2F)
    W = "%s %s %s %s %s" % (p3F, p0F, rA, rB, p3F)
    bottom = "%s %s %s %s %s" % (p0F, p3F, p2F, p1F, p0F)

    if roofopenings is not None:
        addsurface(False, CompositeSurface, S, roofopenings[0])
        addsurface(False, CompositeSurface, E, roofopenings[1])
        addsurface(False, CompositeSurface, N, roofopenings[2])
        addsurface(False, CompositeSurface, W, roofopenings[3])

    else:
        addsurface(False, CompositeSurface, S)
        addsurface(False, CompositeSurface, E)
        addsurface(False, CompositeSurface, N)
        addsurface(False, CompositeSurface, W)
    if atticbottom is True:
        addsurface(False, CompositeSurface, bottom)

def gabledAttic(CompositeSurface, intcoor, p, r, fel, cel, wallThickness, topThickness, atticbottom=False, roofopenings=None):
    """Constructs the interior of the attic of a gabled roof."""
    [Xa, Ya, Xb, Yb] = intcoor
    rA = str(r[0][0]) + ' ' + str(float(r[0][1]) + wallThickness) + ' ' + str(cel)
    rB = str(r[1][0]) + ' ' + str(float(r[1][1]) - wallThickness) + ' ' + str(cel)
    p0F = str(Xa) + ' ' + str(Ya) + ' ' + str(fel)
    p1F = str(Xb) + ' ' + str(Ya) + ' ' + str(fel)
    p2F = str(Xb) + ' ' + str(Yb) + ' ' + str(fel)
    p3F = str(Xa) + ' ' + str(Yb) + ' ' + str(fel)
    bottom = "%s %s %s %s %s" % (p0F, p3F, p2F, p1F, p0F)
    S = "%s %s %s %s" % (p0F, p1F, rA, p0F)
    E = "%s %s %s %s %s" % (p1F, p2F, rB, rA, p1F)
    N = "%s %s %s %s" % (p2F, p3F, rB, p2F)
    W = "%s %s %s %s %s" % (p3F, p0F, rA, rB, p3F)

    if roofopenings is not None:
        addsurface(False, CompositeSurface, S, roofopenings[0])
        addsurface(False, CompositeSurface, E, roofopenings[1])
        addsurface(False, CompositeSurface, N, roofopenings[2])
        addsurface(False, CompositeSurface, W, roofopenings[3])

    else:
        addsurface(False, CompositeSurface, S)
        addsurface(False, CompositeSurface, E)
        addsurface(False, CompositeSurface, N)
        addsurface(False, CompositeSurface, W)

    if atticbottom is True:
        addsurface(False, CompositeSurface, bottom)

def pyramidalAttic(CompositeSurface, intcoor, p, r, fel, cel, wallThickness, topThickness, atticbottom=False, roofopenings=None):
    """Constructs the interior of the attic of a pyramidal roof."""
    [Xa, Ya, Xb, Yb] = intcoor
    rA = str(r[0][0]) + ' ' + str(r[0][1]) + ' ' + str(cel)
    p0F = str(Xa) + ' ' + str(Ya) + ' ' + str(fel)
    p1F = str(Xb) + ' ' + str(Ya) + ' ' + str(fel)
    p2F = str(Xb) + ' ' + str(Yb) + ' ' + str(fel)
    p3F = str(Xa) + ' ' + str(Yb) + ' ' + str(fel)
    bottom = "%s %s %s %s %s" % (p0F, p3F, p2F, p1F, p0F)
    S = "%s %s %s %s" % (p0F, p1F, rA, p0F)
    E = "%s %s %s %s" % (p1F, p2F, rA, p1F)
    N = "%s %s %s %s" % (p2F, p3F, rA, p2F)
    W = "%s %s %s %s" % (p3F, p0F, rA, p3F)
    addsurface(False, CompositeSurface, bottom)
    addsurface(False, CompositeSurface, S)
    addsurface(False, CompositeSurface, E)
    addsurface(False, CompositeSurface, N)
    addsurface(False, CompositeSurface, W)

    if roofopenings is not None:
        addsurface(False, CompositeSurface, S, roofopenings[0])
        addsurface(False, CompositeSurface, E, roofopenings[1])
        addsurface(False, CompositeSurface, N, roofopenings[2])
        addsurface(False, CompositeSurface, W, roofopenings[3])

    else:
        addsurface(False, CompositeSurface, S)
        addsurface(False, CompositeSurface, E)
        addsurface(False, CompositeSurface, N)
        addsurface(False, CompositeSurface, W)
    if atticbottom is True:
        addsurface(False, CompositeSurface, bottom)

def shedAttic(CompositeSurface, intcoor, p, r, fel, cel, wallThickness, topThickness, atticbottom=False, roofopenings=None):
    """Constructs the interior of the attic of a shed roof."""
    [Xa, Ya, Xb, Yb] = intcoor
    rA = str(float(r[0][0]) + wallThickness) + ' ' + str(float(r[0][1]) + wallThickness) + ' ' + str(cel)
    rB = str(float(r[1][0]) + wallThickness) + ' ' + str(float(r[1][1]) - wallThickness) + ' ' + str(cel)
    p0F = str(Xa) + ' ' + str(Ya) + ' ' + str(fel)
    p1F = str(Xb) + ' ' + str(Ya) + ' ' + str(fel)
    p2F = str(Xb) + ' ' + str(Yb) + ' ' + str(fel)
    p3F = str(Xa) + ' ' + str(Yb) + ' ' + str(fel)
    bottom = "%s %s %s %s %s" % (p0F, p3F, p2F, p1F, p0F)
    top = "%s %s %s %s %s" % (rA, p1F, p2F, rB, rA)
    S = "%s %s %s %s" % (p0F, p1F, rA, p0F)
    N = "%s %s %s %s" % (p2F, p3F, rB, p2F)
    W = "%s %s %s %s %s" % (p0F, rA, rB, p3F, p0F)
    addsurface(False, CompositeSurface, bottom)
    addsurface(False, CompositeSurface, top)
    addsurface(False, CompositeSurface, S)
    addsurface(False, CompositeSurface, N)
    addsurface(False, CompositeSurface, W)

    if roofopenings is not None:
        addsurface(False, CompositeSurface, S, roofopenings[0])
        #addsurface(False, CompositeSurface, E, roofopenings[1])
        addsurface(False, CompositeSurface, N, roofopenings[2])
        addsurface(False, CompositeSurface, W, roofopenings[3])

    else:
        addsurface(False, CompositeSurface, S)
        #addsurface(False, CompositeSurface, E)
        addsurface(False, CompositeSurface, N)
        addsurface(False, CompositeSurface, W)
    if atticbottom is True:
        addsurface(False, CompositeSurface, bottom)

def flatRoof(XMLelement, p, r, override_wall=None, semantics=None, openings=None, roofopenings=None, rfWindows=None, embrasure=None, pList=None):
    """Constructs a building with a flat roof."""
    #-- Top face / Roof Surface
    faceTop = "%s %s %s %s %s" % (p[4], p[5], p[6], p[7], p[4])

    #-- Wall Surface
    face0 = "%s %s %s %s %s" % (p[0], p[1], p[5], p[4], p[0])
    if override_wall:
        face1 = override_wall['wall']
    else:
        face1 = "%s %s %s %s %s" % (p[5], p[1], p[2], p[6], p[5])
    face2 = "%s %s %s %s %s" % (p[2], p[3], p[7], p[6], p[2])
    face3 = "%s %s %s %s %s" % (p[3], p[0], p[4], p[7], p[3])

    if openings:
        holes, opns = wallOpeningOrganiser(openings)
    else:
        holes = None
        opns = None

    if embrasure and openings:
        embO = embrasuresGeometry(openings, pList, embrasure)        


    if semantics:
        #-- Roofs
        if roofopenings:
            multiSurface2(XMLelement, faceTop, "RoofSurface", roofopenings[1], 3, rfWindows[1])
        else:
            multiSurface(XMLelement, faceTop, "RoofSurface", None)
        #-- Walls
        if openings:
            if embrasure:
                multiSurfaceWithEmbrasure(XMLelement, face0, "WallSurface", holes[0], 3, embO[0])
            else:
                multiSurface(XMLelement, face0, "WallSurface", holes[0], 3, opns[0])
        else:
            multiSurface(XMLelement, face0, "WallSurface", None)
        if openings:
            if embrasure:
                multiSurfaceWithEmbrasure(XMLelement, face1, "WallSurface", holes[1], 3, embO[1])
            else:
                multiSurface(XMLelement, face1, "WallSurface", holes[1], 3, opns[1])
        else:    
            multiSurface(XMLelement, face1, "WallSurface", None)
        if openings:
            if embrasure:
                multiSurfaceWithEmbrasure(XMLelement, face2, "WallSurface", holes[2], 3, embO[2])
            else:
                multiSurface(XMLelement, face2, "WallSurface", holes[2], 3, opns[2])
        else:    
            multiSurface(XMLelement, face2, "WallSurface", None)
        if openings:
            if embrasure:
                multiSurfaceWithEmbrasure(XMLelement, face3, "WallSurface", holes[3], 3, embO[3])
            else:
                multiSurface(XMLelement, face3, "WallSurface", holes[3], 3, opns[3])
        else:    
            multiSurface(XMLelement, face3, "WallSurface", None)

        #-- Building part
        for fc in override_wall['rest']:
            multiSurface(XMLelement, fc, "WallSurface", None)
        for fc in override_wall['roof']:
            multiSurface(XMLelement, fc, "RoofSurface", None)
        for fc in override_wall['outerfloor']:
            multiSurface(XMLelement, fc, "OuterFloorSurface", None)

    else:
        addsurface(False, XMLelement, faceTop)
        if holes is not None and embrasure:
            addSurfaceWithEmbrasure(False, XMLelement, face0, holes[0], embO[0])
            addSurfaceWithEmbrasure(False, XMLelement, face1, holes[1], embO[1])
            addSurfaceWithEmbrasure(False, XMLelement, face2, holes[2], embO[2])
            addSurfaceWithEmbrasure(False, XMLelement, face3, holes[3], embO[3])            
        else:
            addsurface(False, XMLelement, face0)
            addsurface(False, XMLelement, face1)
            addsurface(False, XMLelement, face2)
            addsurface(False, XMLelement, face3)

        for fc in override_wall['rest']:
            addsurface(False, XMLelement, fc)
        for fc in override_wall['roof']:
            addsurface(False, XMLelement, fc)
        for fc in override_wall['outerfloor']:
            addsurface(False, XMLelement, fc)


def roofOverhangs(XMLelement, overhangs, interiors, semantics=None):
    """Add surfaces for overhangs."""
    i = 0
    if semantics:
        for overhang in overhangs:
            multiSurface(XMLelement, overhang, "RoofSurface", interiors, 3)
            i += 1
    else:
        for overhang in overhangs:
            plainMultiSurface(XMLelement, overhang)
            i += 1


def openingRing(op, p):
    """Makes a linear ring of the feature (opening)."""
    X = op['origin'][0]
    Y = op['origin'][1]
    width = op['size'][0]
    height = op['size'][1]

    if op['wall'] == 0:
        ring = "%s %s %s " % (p[0][0]+X, p[0][1], p[0][2]+Y)
        ring+= "%s %s %s " % (p[0][0]+X, p[0][1], p[0][2]+Y+height)
        ring+= "%s %s %s " % (p[0][0]+X+width, p[0][1], p[0][2]+Y+height)
        ring+= "%s %s %s " % (p[0][0]+X+width, p[0][1], p[0][2]+Y)
        ring+= "%s %s %s" % (p[0][0]+X, p[0][1], p[0][2]+Y)
    elif op['wall'] == 1:
        ring = "%s %s %s " % (p[1][0], p[1][1]+X, p[1][2]+Y)
        ring+= "%s %s %s " % (p[1][0], p[1][1]+X, p[1][2]+Y+height)
        ring+= "%s %s %s " % (p[1][0], p[1][1]+X+width, p[1][2]+Y+height)
        ring+= "%s %s %s " % (p[1][0], p[1][1]+X+width, p[1][2]+Y)
        ring+= "%s %s %s" % (p[1][0], p[1][1]+X, p[1][2]+Y)
    elif op['wall'] == 2:
        ring = "%s %s %s " % (p[2][0]-X, p[2][1], p[2][2]+Y)
        ring+= "%s %s %s " % (p[2][0]-X, p[2][1], p[2][2]+Y+height)
        ring+= "%s %s %s " % (p[2][0]-X-width, p[2][1], p[2][2]+Y+height)
        ring+= "%s %s %s " % (p[2][0]-X-width, p[2][1], p[2][2]+Y)
        ring+= "%s %s %s" % (p[2][0]-X, p[2][1], p[2][2]+Y)
    elif op['wall'] == 3:
        ring = "%s %s %s " % (p[3][0], p[3][1]-X, p[3][2]+Y)
        ring+= "%s %s %s " % (p[3][0], p[3][1]-X, p[3][2]+Y+height)
        ring+= "%s %s %s " % (p[3][0], p[3][1]-X-width, p[3][2]+Y+height)
        ring+= "%s %s %s " % (p[3][0], p[3][1]-X-width, p[3][2]+Y)
        ring+= "%s %s %s" % (p[3][0], p[3][1]-X, p[3][2]+Y)

    else:
        raise ValueError("The door is positioned on an unknown wall.")

    return ring

def embrasuresGeometry(openings, p, embrasure):
    """Makes a linear ring of the feature (opening) with embrasure."""

    embO = [[], [], [], []]

    j = 0

    for t in openings:

        if j == 0:
            currentType = 'Door'
        elif j == 1:
            currentType = 'Window'

        j += 1

        if type(t) is not list:
            t = [t]
        for op in t:
            if op == '':
                continue
            X = float(op['origin'][0])
            Y = float(op['origin'][1])
            width = float(op['size'][0])
            height = float(op['size'][1])

            odict = {}

            if op['wall'] == 0:

                W0 = "%s %s %s" % (p[0][0]+X, p[0][1], p[0][2]+Y)
                W1 = "%s %s %s" % (p[0][0]+X+width, p[0][1], p[0][2]+Y)
                W2 = "%s %s %s" % (p[0][0]+X+width, p[0][1], p[0][2]+Y+height)
                W3 = "%s %s %s" % (p[0][0]+X, p[0][1], p[0][2]+Y+height)

                O0 = "%s %s %s" % (p[0][0]+X, p[0][1]+embrasure, p[0][2]+Y)
                O1 = "%s %s %s" % (p[0][0]+X+width, p[0][1]+embrasure, p[0][2]+Y)
                O2 = "%s %s %s" % (p[0][0]+X+width, p[0][1]+embrasure, p[0][2]+Y+height)
                O3 = "%s %s %s" % (p[0][0]+X, p[0][1]+embrasure, p[0][2]+Y+height)

            elif op['wall'] == 1:

                W0 = "%s %s %s" % (p[1][0], p[1][1]+X, p[1][2]+Y)
                W1 = "%s %s %s" % (p[1][0], p[1][1]+X+width, p[1][2]+Y)
                W2 = "%s %s %s" % (p[1][0], p[1][1]+X+width, p[1][2]+Y+height)
                W3 = "%s %s %s" % (p[1][0], p[1][1]+X, p[1][2]+Y+height)

                O0 = "%s %s %s" % (p[1][0]-embrasure, p[1][1]+X, p[1][2]+Y)
                O1 = "%s %s %s" % (p[1][0]-embrasure, p[1][1]+X+width, p[1][2]+Y)
                O2 = "%s %s %s" % (p[1][0]-embrasure, p[1][1]+X+width, p[1][2]+Y+height)
                O3 = "%s %s %s" % (p[1][0]-embrasure, p[1][1]+X, p[1][2]+Y+height)


            elif op['wall'] == 2:

                W0 = "%s %s %s" % (p[2][0]-X, p[2][1], p[2][2]+Y)
                W1 = "%s %s %s" % (p[2][0]-X-width, p[2][1], p[2][2]+Y)
                W2 = "%s %s %s" % (p[2][0]-X-width, p[2][1], p[2][2]+Y+height)
                W3 = "%s %s %s" % (p[2][0]-X, p[2][1], p[2][2]+Y+height)

                O0 = "%s %s %s" % (p[2][0]-X, p[2][1]-embrasure, p[2][2]+Y)
                O1 = "%s %s %s" % (p[2][0]-X-width, p[2][1]-embrasure, p[2][2]+Y)
                O2 = "%s %s %s" % (p[2][0]-X-width, p[2][1]-embrasure, p[2][2]+Y+height)
                O3 = "%s %s %s" % (p[2][0]-X, p[2][1]-embrasure, p[2][2]+Y+height)

            elif op['wall'] == 3:

                W0 = "%s %s %s" % (p[3][0], p[3][1]-X, p[3][2]+Y)
                W1 = "%s %s %s" % (p[3][0], p[3][1]-X-width, p[3][2]+Y)
                W2 = "%s %s %s" % (p[3][0], p[3][1]-X-width, p[3][2]+Y+height)
                W3 = "%s %s %s" % (p[3][0], p[3][1]-X, p[3][2]+Y+height)

                O0 = "%s %s %s" % (p[3][0]+embrasure, p[3][1]-X, p[3][2]+Y)
                O1 = "%s %s %s" % (p[3][0]+embrasure, p[3][1]-X-width, p[3][2]+Y)
                O2 = "%s %s %s" % (p[3][0]+embrasure, p[3][1]-X-width, p[3][2]+Y+height)
                O3 = "%s %s %s" % (p[3][0]+embrasure, p[3][1]-X, p[3][2]+Y+height)

            else:
                raise ValueError("The door is positioned on an unknown wall.")
##-- Unchanged
            ringW = O0 + ' '
            ringW+= O1 + ' '
            ringW+= O2 + ' '
            ringW+= O3 + ' '
            ringW+= O0

            ring0 = W0 + ' '
            ring0+= O0 + ' '
            ring0+= O3 + ' '
            ring0+= W3 + ' '
            ring0+= W0

            ring1 = W0 + ' '
            ring1+= W1 + ' '
            ring1+= O1 + ' '
            ring1+= O0 + ' '
            ring1+= W0

            ring2 = W2 + ' '
            ring2+= O2 + ' '
            ring2+= O1 + ' '
            ring2+= W1 + ' '
            ring2+= W2

            ring3 = W2 + ' '
            ring3+= W3 + ' '
            ring3+= O3 + ' '
            ring3+= O2 + ' '
            ring3+= W2


            odict['surfaces'] = [ring0, ring1, ring2, ring3]
            odict['openings'] = [ringW]
            odict['type'] = currentType

            embO[op['wall']].append(odict)

    return embO

def addsurface(skipsm, CompositeSurface, coords, interior=None):
        """
        Adds a surface to the CompositeSurface (and others).
        Input: coordinates of the LinearRing of the surface to be added to the CompositeSurface.
        Output: Upgraded CompositeSurface.
        If skipsm is toggled, it will skip the creation of the <gml:SurfaceMember>
        """
        if skipsm is False:
            surfaceMember = etree.SubElement(CompositeSurface, "{%s}surfaceMember" % ns_gml)
            Polygon = etree.SubElement(surfaceMember, "{%s}Polygon" % ns_gml)
        else:
            Polygon = etree.SubElement(CompositeSurface, "{%s}Polygon" % ns_gml)
        if ASSIGNID:
            Polygon.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
        PolygonExterior = etree.SubElement(Polygon, "{%s}exterior" % ns_gml)
        LinearRing = etree.SubElement(PolygonExterior, "{%s}LinearRing" % ns_gml)
        posList = etree.SubElement(LinearRing, "{%s}posList" % ns_gml)
        posList.text = coords

        if interior and interior[0] is not None:
            for hole in interior:
                PolygonInterior = etree.SubElement(Polygon, "{%s}interior" % ns_gml)
                LinearRing = etree.SubElement(PolygonInterior, "{%s}LinearRing" % ns_gml)
                posList = etree.SubElement(LinearRing, "{%s}posList" % ns_gml)
                posList.text = hole

def addSurfaceWithEmbrasure(skipsm, CompositeSurface, coords, interior=None, embO=None):
        """
        Adds a surface to the CompositeSurface.
        Input: coordinates of the LinearRing of the surface to be added to the CompositeSurface.
        Output: Upgraded CompositeSurface.
        If skipsm is toggled, it will skip the creation of the <gml:SurfaceMember>
        """
        if skipsm is False:
            surfaceMember = etree.SubElement(CompositeSurface, "{%s}surfaceMember" % ns_gml)
            Polygon = etree.SubElement(surfaceMember, "{%s}Polygon" % ns_gml)
        else:
            Polygon = etree.SubElement(CompositeSurface, "{%s}Polygon" % ns_gml)
        if ASSIGNID:
            Polygon.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
        PolygonExterior = etree.SubElement(Polygon, "{%s}exterior" % ns_gml)
        LinearRing = etree.SubElement(PolygonExterior, "{%s}LinearRing" % ns_gml)
        posList = etree.SubElement(LinearRing, "{%s}posList" % ns_gml)
        posList.text = coords

        if interior and interior[0] is not None:
            for hole in interior:
                PolygonInterior = etree.SubElement(Polygon, "{%s}interior" % ns_gml)
                LinearRing = etree.SubElement(PolygonInterior, "{%s}LinearRing" % ns_gml)
                posList = etree.SubElement(LinearRing, "{%s}posList" % ns_gml)
                posList.text = hole

        for opening in embO:
            for s in opening['surfaces']:
                surfaceMember = etree.SubElement(CompositeSurface, "{%s}surfaceMember" % ns_gml)
                Polygon = etree.SubElement(surfaceMember, "{%s}Polygon" % ns_gml)
                if ASSIGNID:
                    Polygon.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
                PolygonExterior = etree.SubElement(Polygon, "{%s}exterior" % ns_gml)
                LinearRing = etree.SubElement(PolygonExterior, "{%s}LinearRing" % ns_gml)
                posList = etree.SubElement(LinearRing, "{%s}posList" % ns_gml)
                posList.text = s
            for o in opening['openings']:
                DoorsurfaceMember = etree.SubElement(CompositeSurface, "{%s}surfaceMember" % ns_gml)
                DoorPolygon = etree.SubElement(DoorsurfaceMember, "{%s}Polygon" % ns_gml)
                if ASSIGNID:
                    DoorPolygon.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
                DoorPolygonExterior = etree.SubElement(DoorPolygon, "{%s}exterior" % ns_gml)
                DoorLinearRing = etree.SubElement(DoorPolygonExterior, "{%s}LinearRing" % ns_gml)
                DoorposList = etree.SubElement(DoorLinearRing, "{%s}posList" % ns_gml)
                DoorposList.text = o#['ring']

def interiorDormer(cs, d, side):
    """Interior of a dormer."""
    dList, dListGML = d
    d1 = dListGML[0] + ' ' + dListGML[1] + ' ' + dListGML[4] + ' ' + dListGML[0]
    d2 = dListGML[0] + ' ' + dListGML[4] + ' ' + dListGML[5] + ' ' + dListGML[3] + ' ' + dListGML[0]
    d3 = dListGML[5] + ' ' + dListGML[2] + ' ' + dListGML[3] + ' ' + dListGML[5]
    addsurface(False, cs, d1) 
    addsurface(False, cs, d2) 
    addsurface(False, cs, d3)
    d4 = dListGML[4] + ' ' + dListGML[1] + ' ' + dListGML[2] + ' ' + dListGML[5] + ' ' + dListGML[4]
    addsurface(False, cs, d4)

def buildinginstallation(bldg, kind, d, semantics=0, window=None, side=None, embrasure=None):
    """Generate a building installation: for dormers and chimneys."""
    dList, dListGML = d

    if window is not None:
        pass

    obi = etree.SubElement(bldg, "{%s}outerBuildingInstallation" % ns_bldg)
    bi = etree.SubElement(obi, "{%s}BuildingInstallation" % ns_bldg)


    def binosemantics(XMLelement, coords, window = None):
        MultiSurface = etree.SubElement(XMLelement, "{%s}MultiSurface" % ns_gml)
        surfaceMember = etree.SubElement(MultiSurface, "{%s}surfaceMember" % ns_gml)
        Polygon = etree.SubElement(surfaceMember, "{%s}Polygon" % ns_gml)
        if ASSIGNID:
            Polygon.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
        PolygonExterior = etree.SubElement(Polygon, "{%s}exterior" % ns_gml)
        LinearRing = etree.SubElement(PolygonExterior, "{%s}LinearRing" % ns_gml)
        posList = etree.SubElement(LinearRing, "{%s}posList" % ns_gml)
        posList.text = coords

        if window is not None:

            PolygonInterior = etree.SubElement(Polygon, "{%s}interior" % ns_gml)
            LinearRing = etree.SubElement(PolygonInterior, "{%s}LinearRing" % ns_gml)
            posList = etree.SubElement(LinearRing, "{%s}posList" % ns_gml)
            posList.text = window 

    def bisemantics(XMLelement, coords, semantics, window = None, fillHole = True):
        boundedBy = etree.SubElement(XMLelement, "{%s}boundedBy" % ns_bldg)
        semanticSurface = etree.SubElement(boundedBy, "{%s}%s" % (ns_bldg, semantics))     
        lod3geometry = etree.SubElement(semanticSurface, "{%s}lod3MultiSurface" % ns_bldg)   
        MultiSurface = etree.SubElement(lod3geometry, "{%s}MultiSurface" % ns_gml)
        surfaceMember = etree.SubElement(MultiSurface, "{%s}surfaceMember" % ns_gml)
        Polygon = etree.SubElement(surfaceMember, "{%s}Polygon" % ns_gml)
        if ASSIGNID:
            Polygon.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
        PolygonExterior = etree.SubElement(Polygon, "{%s}exterior" % ns_gml)
        LinearRing = etree.SubElement(PolygonExterior, "{%s}LinearRing" % ns_gml)
        posList = etree.SubElement(LinearRing, "{%s}posList" % ns_gml)
        posList.text = coords

        if window is not None:

            PolygonInterior = etree.SubElement(Polygon, "{%s}interior" % ns_gml)
            LinearRing = etree.SubElement(PolygonInterior, "{%s}LinearRing" % ns_gml)
            posList = etree.SubElement(LinearRing, "{%s}posList" % ns_gml)
            posList.text = GMLreversedRing(window)

            if fillHole is True:

                gmlopening = etree.SubElement(semanticSurface, "{%s}opening" % ns_bldg)
                gmlwin = etree.SubElement(gmlopening, "{%s}Window" % ns_bldg)
                lod3MultiSurface = etree.SubElement(gmlwin, "{%s}lod3MultiSurface" % ns_bldg)
                DoorMultiSurface = etree.SubElement(lod3MultiSurface, "{%s}MultiSurface" % ns_gml)
                DoorsurfaceMember = etree.SubElement(DoorMultiSurface, "{%s}surfaceMember" % ns_gml)
                DoorPolygon = etree.SubElement(DoorsurfaceMember, "{%s}Polygon" % ns_gml)
                if ASSIGNID:
                    DoorPolygon.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
                DoorPolygonExterior = etree.SubElement(DoorPolygon, "{%s}exterior" % ns_gml)
                DoorLinearRing = etree.SubElement(DoorPolygonExterior, "{%s}LinearRing" % ns_gml)
                DoorposList = etree.SubElement(DoorLinearRing, "{%s}posList" % ns_gml)
                DoorposList.text = window

    def bisemanticsMulti(XMLelement, coords, semantics, window = None):
        boundedBy = etree.SubElement(XMLelement, "{%s}boundedBy" % ns_bldg)
        semanticSurface = etree.SubElement(boundedBy, "{%s}%s" % (ns_bldg, semantics))     
        lod3geometry = etree.SubElement(semanticSurface, "{%s}lod3MultiSurface" % ns_bldg)   
        MultiSurface = etree.SubElement(lod3geometry, "{%s}MultiSurface" % ns_gml)
        surfaceMember = etree.SubElement(MultiSurface, "{%s}surfaceMember" % ns_gml)

        for coord in coords:

            Polygon = etree.SubElement(surfaceMember, "{%s}Polygon" % ns_gml)
            if ASSIGNID:
                Polygon.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
            PolygonExterior = etree.SubElement(Polygon, "{%s}exterior" % ns_gml)
            LinearRing = etree.SubElement(PolygonExterior, "{%s}LinearRing" % ns_gml)
            posList = etree.SubElement(LinearRing, "{%s}posList" % ns_gml)
            posList.text = coord

        if window is not None:

            gmlopening = etree.SubElement(semanticSurface, "{%s}opening" % ns_bldg)
            gmlwin = etree.SubElement(gmlopening, "{%s}Window" % ns_bldg)
            lod3MultiSurface = etree.SubElement(gmlwin, "{%s}lod3MultiSurface" % ns_bldg)
            DoorMultiSurface = etree.SubElement(lod3MultiSurface, "{%s}MultiSurface" % ns_gml)
            DoorsurfaceMember = etree.SubElement(DoorMultiSurface, "{%s}surfaceMember" % ns_gml)
            DoorPolygon = etree.SubElement(DoorsurfaceMember, "{%s}Polygon" % ns_gml)
            if ASSIGNID:
                DoorPolygon.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
            DoorPolygonExterior = etree.SubElement(DoorPolygon, "{%s}exterior" % ns_gml)
            DoorLinearRing = etree.SubElement(DoorPolygonExterior, "{%s}LinearRing" % ns_gml)
            DoorposList = etree.SubElement(DoorLinearRing, "{%s}posList" % ns_gml)
            DoorposList.text = window


    if semantics == 0:
        if kind == 'dormer':
            lod3geometry = etree.SubElement(bi, "{%s}lod3Geometry" % ns_bldg)
            d1 = dListGML[0] + ' ' + dListGML[1] + ' ' + dListGML[4] + ' ' + dListGML[0]
            d2 = dListGML[0] + ' ' + dListGML[4] + ' ' + dListGML[5] + ' ' + dListGML[3] + ' ' + dListGML[0]
            d3 = dListGML[5] + ' ' + dListGML[2] + ' ' + dListGML[3] + ' ' + dListGML[5]
            binosemantics(lod3geometry, d1) 
            binosemantics(lod3geometry, d2) 
            binosemantics(lod3geometry, d3)

            if window is None:
                d4 = dListGML[4] + ' ' + dListGML[1] + ' ' + dListGML[2] + ' ' + dListGML[5] + ' ' + dListGML[4]
                binosemantics(lod3geometry, d4)

            if window is not None:

                if embrasure is not None and embrasure > 0.0:

                    d4 = dListGML[4] + ' ' + dListGML[1] + ' ' + dListGML[2] + ' ' + dListGML[5] + ' ' + dListGML[4]

                    if side == 1:
                        dw = [[], [], [], []]
                        ew = [[], [], [], []]

                        dw[0] = [dList[4][0], dList[4][1] + window, dList[4][2] - window]
                        dw[1] = [dList[1][0], dList[1][1] + window, dList[1][2] + window]
                        dw[2] = [dList[2][0], dList[2][1] - window, dList[2][2] + window]
                        dw[3] = [dList[5][0], dList[5][1] - window, dList[5][2] - window]

                        ew[0] = [dList[4][0] - embrasure, dList[4][1] + window, dList[4][2] - window]
                        ew[1] = [dList[1][0] - embrasure, dList[1][1] + window, dList[1][2] + window]
                        ew[2] = [dList[2][0] - embrasure, dList[2][1] - window, dList[2][2] + window]
                        ew[3] = [dList[5][0] - embrasure, dList[5][1] - window, dList[5][2] - window]

                    elif side == 3:
                        dw = [[], [], [], []]
                        ew = [[], [], [], []]

                        dw[0] = [dList[4][0], dList[4][1] - window, dList[4][2] - window]
                        dw[1] = [dList[1][0], dList[1][1] - window, dList[1][2] + window]
                        dw[2] = [dList[2][0], dList[2][1] + window, dList[2][2] + window]
                        dw[3] = [dList[5][0], dList[5][1] + window, dList[5][2] - window]

                        ew[0] = [dList[4][0] + embrasure, dList[4][1] - window, dList[4][2] - window]
                        ew[1] = [dList[1][0] + embrasure, dList[1][1] - window, dList[1][2] + window]
                        ew[2] = [dList[2][0] + embrasure, dList[2][1] + window, dList[2][2] + window]
                        ew[3] = [dList[5][0] + embrasure, dList[5][1] + window, dList[5][2] - window]

                    elif side == 0:
                        dw = [[], [], [], []]
                        ew = [[], [], [], []]
                        dw[0] = [dList[4][0] + window, dList[4][1], dList[4][2] - window]
                        dw[1] = [dList[1][0] + window, dList[1][1], dList[1][2] + window]
                        dw[2] = [dList[2][0] - window, dList[2][1], dList[2][2] + window]
                        dw[3] = [dList[5][0] - window, dList[5][1], dList[5][2] - window]

                        ew[0] = [dList[4][0] + window, dList[4][1] + embrasure, dList[4][2] - window]
                        ew[1] = [dList[1][0] + window, dList[1][1] + embrasure, dList[1][2] + window]
                        ew[2] = [dList[2][0] - window, dList[2][1] + embrasure, dList[2][2] + window]
                        ew[3] = [dList[5][0] - window, dList[5][1] + embrasure, dList[5][2] - window]

                    elif side == 2:
                        dw = [[], [], [], []]
                        ew = [[], [], [], []]

                        dw[0] = [dList[4][0] - window, dList[4][1], dList[4][2] - window]
                        dw[1] = [dList[1][0] - window, dList[1][1], dList[1][2] + window]
                        dw[2] = [dList[2][0] + window, dList[2][1], dList[2][2] + window]
                        dw[3] = [dList[5][0] + window, dList[5][1], dList[5][2] - window]

                        ew[0] = [dList[4][0] - window, dList[4][1] - embrasure, dList[4][2] - window]
                        ew[1] = [dList[1][0] - window, dList[1][1] - embrasure, dList[1][2] + window]
                        ew[2] = [dList[2][0] + window, dList[2][1] - embrasure, dList[2][2] + window]
                        ew[3] = [dList[5][0] + window, dList[5][1] - embrasure, dList[5][2] - window]      

                    dwring = GMLPointList(dw[0]) + ' ' + GMLPointList(dw[3]) + ' ' + GMLPointList(dw[2]) + ' ' + GMLPointList(dw[1]) + ' ' + GMLPointList(dw[0])
                    binosemantics(lod3geometry, d4, dwring)


                    dw0 = GMLPointList(dw[0]) + ' ' + GMLPointList(dw[1]) + ' ' + GMLPointList(ew[1]) + ' ' + GMLPointList(ew[0]) + ' ' + GMLPointList(dw[0])
                    dw1 = GMLPointList(dw[1]) + ' ' + GMLPointList(dw[2]) + ' ' + GMLPointList(ew[2]) + ' ' + GMLPointList(ew[1]) + ' ' + GMLPointList(dw[1])
                    dw2 = GMLPointList(dw[3]) + ' ' + GMLPointList(ew[3]) + ' ' + GMLPointList(ew[2]) + ' ' + GMLPointList(dw[2]) + ' ' + GMLPointList(dw[3])
                    dw3 = GMLPointList(dw[3]) + ' ' + GMLPointList(dw[0]) + ' ' + GMLPointList(ew[0]) + ' ' + GMLPointList(ew[3]) + ' ' + GMLPointList(dw[3])

                    ew0 = GMLPointList(ew[0]) + ' ' + GMLPointList(ew[1]) + ' ' + GMLPointList(ew[2]) + ' ' + GMLPointList(ew[3]) + ' ' + GMLPointList(ew[0])

                    for bipoly in [dw0, dw1, dw2, dw3]:
                        binosemantics(lod3geometry, bipoly)
                    binosemantics(lod3geometry, ew0)

                else:

                    d4 = dListGML[4] + ' ' + dListGML[1] + ' ' + dListGML[2] + ' ' + dListGML[5] + ' ' + dListGML[4]
                    if side == 1:
                        dw = [[], [], [], []]
                        ew = [[], [], [], []]

                        dw[0] = [dList[4][0], dList[4][1] + window, dList[4][2] - window]
                        dw[1] = [dList[1][0], dList[1][1] + window, dList[1][2] + window]
                        dw[2] = [dList[2][0], dList[2][1] - window, dList[2][2] + window]
                        dw[3] = [dList[5][0], dList[5][1] - window, dList[5][2] - window]

                        ew[0] = [dList[4][0], dList[4][1] + window, dList[4][2] - window]
                        ew[1] = [dList[1][0], dList[1][1] + window, dList[1][2] + window]
                        ew[2] = [dList[2][0], dList[2][1] - window, dList[2][2] + window]
                        ew[3] = [dList[5][0], dList[5][1] - window, dList[5][2] - window]

                    elif side == 3:
                        dw = [[], [], [], []]
                        ew = [[], [], [], []]

                        dw[0] = [dList[4][0], dList[4][1] - window, dList[4][2] - window]
                        dw[1] = [dList[1][0], dList[1][1] - window, dList[1][2] + window]
                        dw[2] = [dList[2][0], dList[2][1] + window, dList[2][2] + window]
                        dw[3] = [dList[5][0], dList[5][1] + window, dList[5][2] - window]

                        ew[0] = [dList[4][0], dList[4][1] - window, dList[4][2] - window]
                        ew[1] = [dList[1][0], dList[1][1] - window, dList[1][2] + window]
                        ew[2] = [dList[2][0], dList[2][1] + window, dList[2][2] + window]
                        ew[3] = [dList[5][0], dList[5][1] + window, dList[5][2] - window]

                    elif side == 0:
                        dw = [[], [], [], []]
                        ew = [[], [], [], []]
                        dw[0] = [dList[4][0] + window, dList[4][1], dList[4][2] - window]
                        dw[1] = [dList[1][0] + window, dList[1][1], dList[1][2] + window]
                        dw[2] = [dList[2][0] - window, dList[2][1], dList[2][2] + window]
                        dw[3] = [dList[5][0] - window, dList[5][1], dList[5][2] - window]

                        ew[0] = [dList[4][0] + window, dList[4][1], dList[4][2] - window]
                        ew[1] = [dList[1][0] + window, dList[1][1], dList[1][2] + window]
                        ew[2] = [dList[2][0] - window, dList[2][1], dList[2][2] + window]
                        ew[3] = [dList[5][0] - window, dList[5][1], dList[5][2] - window]

                    elif side == 2:
                        dw = [[], [], [], []]
                        ew = [[], [], [], []]
                        dw[0] = [dList[4][0] - window, dList[4][1], dList[4][2] - window]
                        dw[1] = [dList[1][0] - window, dList[1][1], dList[1][2] + window]
                        dw[2] = [dList[2][0] + window, dList[2][1], dList[2][2] + window]
                        dw[3] = [dList[5][0] + window, dList[5][1], dList[5][2] - window]

                        ew[0] = [dList[4][0] - window, dList[4][1], dList[4][2] - window]
                        ew[1] = [dList[1][0] - window, dList[1][1], dList[1][2] + window]
                        ew[2] = [dList[2][0] + window, dList[2][1], dList[2][2] + window]
                        ew[3] = [dList[5][0] + window, dList[5][1], dList[5][2] - window]               

                    dwring = GMLPointList(dw[0]) + ' ' + GMLPointList(dw[3]) + ' ' + GMLPointList(dw[2]) + ' ' + GMLPointList(dw[1]) + ' ' + GMLPointList(dw[0])
                    #ew0 = GMLPointList(ew[0]) + ' ' + GMLPointList(ew[1]) + ' ' + GMLPointList(ew[2]) + ' ' + GMLPointList(ew[3]) + ' ' + GMLPointList(ew[0])
                    binosemantics(lod3geometry, d4, dwring)
                    #binosemantics(lod3geometry, ew0)

        elif kind == 'chimney':
            lod3geometry = etree.SubElement(bi, "{%s}lod3Geometry" % ns_bldg)
            d1 = dListGML[0] + ' ' + dListGML[1] + ' ' + dListGML[4] + ' ' + dListGML[7] + ' ' + dListGML[0]
            d2 = dListGML[3] + ' ' + dListGML[6] + ' ' + dListGML[5] + ' ' + dListGML[2] + ' ' + dListGML[3]
            d3 = dListGML[0] + ' ' + dListGML[7] + ' ' + dListGML[6] + ' ' + dListGML[3] + ' ' + dListGML[0]
            d4 = dListGML[4] + ' ' + dListGML[1] + ' ' + dListGML[2] + ' ' + dListGML[5] + ' ' + dListGML[4]
            binosemantics(lod3geometry, d1) 
            binosemantics(lod3geometry, d2) 
            binosemantics(lod3geometry, d3)
            binosemantics(lod3geometry, d4)

            d5 = dListGML[7] + ' ' + dListGML[4] + ' ' + dListGML[5] + ' ' + dListGML[6] + ' ' + dListGML[7]
            binosemantics(lod3geometry, d5)
            #-- Closure surface in the roof
            # d0 = dListGML[0] + ' ' + dListGML[1] + ' ' + dListGML[2] + ' ' + dListGML[3] + ' ' + dListGML[0]
            # binosemantics(lod3geometry, d0)
            #-- Closure surface in the roof
            d0 = dListGML[0] + ' ' + dListGML[1] + ' ' + dListGML[2] + ' ' + dListGML[3] + ' ' + dListGML[0]
            bisemantics(lod3geometry, d0, "ClosureSurface")

    if semantics == 1:
        if kind == 'dormer':
            d1 = dListGML[0] + ' ' + dListGML[1] + ' ' + dListGML[4] + ' ' + dListGML[0]
            d2 = dListGML[0] + ' ' + dListGML[4] + ' ' + dListGML[5] + ' ' + dListGML[3] + ' ' + dListGML[0]
            d3 = dListGML[5] + ' ' + dListGML[2] + ' ' + dListGML[3] + ' ' + dListGML[5]
            bisemantics(bi, d1, "WallSurface") 
            bisemantics(bi, d2, "RoofSurface") 
            bisemantics(bi, d3, "WallSurface")

            if window is None:

                d4 = dListGML[4] + ' ' + dListGML[1] + ' ' + dListGML[2] + ' ' + dListGML[5] + ' ' + dListGML[4]
                bisemantics(bi, d4, "WallSurface")

            if window is not None:

                #-- Face with the window
                if embrasure is not None and embrasure > 0.0:

                    d4 = dListGML[4] + ' ' + dListGML[1] + ' ' + dListGML[2] + ' ' + dListGML[5] + ' ' + dListGML[4]

                    if side == 1:
                        dw = [[], [], [], []]
                        ew = [[], [], [], []]

                        dw[0] = [dList[4][0], dList[4][1] + window, dList[4][2] - window]
                        dw[1] = [dList[1][0], dList[1][1] + window, dList[1][2] + window]
                        dw[2] = [dList[2][0], dList[2][1] - window, dList[2][2] + window]
                        dw[3] = [dList[5][0], dList[5][1] - window, dList[5][2] - window]

                        ew[0] = [dList[4][0] - embrasure, dList[4][1] + window, dList[4][2] - window]
                        ew[1] = [dList[1][0] - embrasure, dList[1][1] + window, dList[1][2] + window]
                        ew[2] = [dList[2][0] - embrasure, dList[2][1] - window, dList[2][2] + window]
                        ew[3] = [dList[5][0] - embrasure, dList[5][1] - window, dList[5][2] - window]

                    elif side == 3:
                        dw = [[], [], [], []]
                        ew = [[], [], [], []]

                        dw[0] = [dList[4][0], dList[4][1] - window, dList[4][2] - window]
                        dw[1] = [dList[1][0], dList[1][1] - window, dList[1][2] + window]
                        dw[2] = [dList[2][0], dList[2][1] + window, dList[2][2] + window]
                        dw[3] = [dList[5][0], dList[5][1] + window, dList[5][2] - window]

                        ew[0] = [dList[4][0] + embrasure, dList[4][1] - window, dList[4][2] - window]
                        ew[1] = [dList[1][0] + embrasure, dList[1][1] - window, dList[1][2] + window]
                        ew[2] = [dList[2][0] + embrasure, dList[2][1] + window, dList[2][2] + window]
                        ew[3] = [dList[5][0] + embrasure, dList[5][1] + window, dList[5][2] - window]

                    elif side == 0:
                        dw = [[], [], [], []]
                        ew = [[], [], [], []]
                        dw[0] = [dList[4][0] + window, dList[4][1], dList[4][2] - window]
                        dw[1] = [dList[1][0] + window, dList[1][1], dList[1][2] + window]
                        dw[2] = [dList[2][0] - window, dList[2][1], dList[2][2] + window]
                        dw[3] = [dList[5][0] - window, dList[5][1], dList[5][2] - window]

                        ew[0] = [dList[4][0] + window, dList[4][1] + embrasure, dList[4][2] - window]
                        ew[1] = [dList[1][0] + window, dList[1][1] + embrasure, dList[1][2] + window]
                        ew[2] = [dList[2][0] - window, dList[2][1] + embrasure, dList[2][2] + window]
                        ew[3] = [dList[5][0] - window, dList[5][1] + embrasure, dList[5][2] - window]

                    elif side == 2:
                        dw = [[], [], [], []]
                        ew = [[], [], [], []]

                        dw[0] = [dList[4][0] - window, dList[4][1], dList[4][2] - window]
                        dw[1] = [dList[1][0] - window, dList[1][1], dList[1][2] + window]
                        dw[2] = [dList[2][0] + window, dList[2][1], dList[2][2] + window]
                        dw[3] = [dList[5][0] + window, dList[5][1], dList[5][2] - window]

                        ew[0] = [dList[4][0] - window, dList[4][1] - embrasure, dList[4][2] - window]
                        ew[1] = [dList[1][0] - window, dList[1][1] - embrasure, dList[1][2] + window]
                        ew[2] = [dList[2][0] + window, dList[2][1] - embrasure, dList[2][2] + window]
                        ew[3] = [dList[5][0] + window, dList[5][1] - embrasure, dList[5][2] - window]      

                    dwring = GMLPointList(dw[0]) + ' ' + GMLPointList(dw[3]) + ' ' + GMLPointList(dw[2]) + ' ' + GMLPointList(dw[1]) + ' ' + GMLPointList(dw[0])
                    bisemantics(bi, d4, "WallSurface", dwring, False)


                    dw0 = GMLPointList(dw[0]) + ' ' + GMLPointList(dw[1]) + ' ' + GMLPointList(ew[1]) + ' ' + GMLPointList(ew[0]) + ' ' + GMLPointList(dw[0])
                    dw1 = GMLPointList(dw[1]) + ' ' + GMLPointList(dw[2]) + ' ' + GMLPointList(ew[2]) + ' ' + GMLPointList(ew[1]) + ' ' + GMLPointList(dw[1])
                    dw2 = GMLPointList(dw[3]) + ' ' + GMLPointList(ew[3]) + ' ' + GMLPointList(ew[2]) + ' ' + GMLPointList(dw[2]) + ' ' + GMLPointList(dw[3])
                    dw3 = GMLPointList(dw[3]) + ' ' + GMLPointList(dw[0]) + ' ' + GMLPointList(ew[0]) + ' ' + GMLPointList(ew[3]) + ' ' + GMLPointList(dw[3])

                    ew0 = GMLPointList(ew[0]) + ' ' + GMLPointList(ew[1]) + ' ' + GMLPointList(ew[2]) + ' ' + GMLPointList(ew[3]) + ' ' + GMLPointList(ew[0])

                    bisemanticsMulti(bi, [dw0, dw1, dw2, dw3], "WallSurface", ew0)

                else:

                    d4 = dListGML[4] + ' ' + dListGML[1] + ' ' + dListGML[2] + ' ' + dListGML[5] + ' ' + dListGML[4]
                    if side == 1:
                        dw = [[], [], [], []]
                        dw[0] = [dList[4][0], dList[4][1] + window, dList[4][2] - window]
                        dw[1] = [dList[1][0], dList[1][1] + window, dList[1][2] + window]
                        dw[2] = [dList[2][0], dList[2][1] - window, dList[2][2] + window]
                        dw[3] = [dList[5][0], dList[5][1] - window, dList[5][2] - window]
                    elif side == 3:
                        dw = [[], [], [], []]
                        dw[0] = [dList[4][0], dList[4][1] - window, dList[4][2] - window]
                        dw[1] = [dList[1][0], dList[1][1] - window, dList[1][2] + window]
                        dw[2] = [dList[2][0], dList[2][1] + window, dList[2][2] + window]
                        dw[3] = [dList[5][0], dList[5][1] + window, dList[5][2] - window]
                    elif side == 0:
                        dw = [[], [], [], []]
                        dw[0] = [dList[4][0] + window, dList[4][1], dList[4][2] - window]
                        dw[1] = [dList[1][0] + window, dList[1][1], dList[1][2] + window]
                        dw[2] = [dList[2][0] - window, dList[2][1], dList[2][2] + window]
                        dw[3] = [dList[5][0] - window, dList[5][1], dList[5][2] - window]
                    elif side == 2:
                        dw = [[], [], [], []]
                        dw[0] = [dList[4][0] - window, dList[4][1], dList[4][2] - window]
                        dw[1] = [dList[1][0] - window, dList[1][1], dList[1][2] + window]
                        dw[2] = [dList[2][0] + window, dList[2][1], dList[2][2] + window]
                        dw[3] = [dList[5][0] + window, dList[5][1], dList[5][2] - window]                

                    dwring = GMLPointList(dw[0]) + ' ' + GMLPointList(dw[3]) + ' ' + GMLPointList(dw[2]) + ' ' + GMLPointList(dw[1]) + ' ' + GMLPointList(dw[0])
                    ew0 = GMLPointList(dw[0]) + ' ' + GMLPointList(dw[1]) + ' ' + GMLPointList(dw[2]) + ' ' + GMLPointList(dw[3]) + ' ' + GMLPointList(dw[0])
                    bisemantics(bi, d4, "WallSurface", ew0, True)
                    #bisemantics(bi, d4, "WallSurface", dwring, ew0)

        elif kind == 'chimney':
            lod3geometry = etree.SubElement(bi, "{%s}lod3Geometry" % ns_bldg)
            d1 = dListGML[0] + ' ' + dListGML[1] + ' ' + dListGML[4] + ' ' + dListGML[7] + ' ' + dListGML[0]
            d2 = dListGML[3] + ' ' + dListGML[6] + ' ' + dListGML[5] + ' ' + dListGML[2] + ' ' + dListGML[3]
            d3 = dListGML[0] + ' ' + dListGML[7] + ' ' + dListGML[6] + ' ' + dListGML[3] + ' ' + dListGML[0]
            d4 = dListGML[4] + ' ' + dListGML[1] + ' ' + dListGML[2] + ' ' + dListGML[5] + ' ' + dListGML[4]
            bisemantics(lod3geometry, d1, "WallSurface") 
            bisemantics(lod3geometry, d2, "WallSurface") 
            bisemantics(lod3geometry, d3, "WallSurface")
            bisemantics(lod3geometry, d4, "WallSurface")

            #-- Closure surface on the top
            d5 = dListGML[7] + ' ' + dListGML[4] + ' ' + dListGML[5] + ' ' + dListGML[6] + ' ' + dListGML[7]
            bisemantics(lod3geometry, d5, "ClosureSurface")
            #-- Closure surface in the roof
            d0 = dListGML[0] + ' ' + dListGML[1] + ' ' + dListGML[2] + ' ' + dListGML[3] + ' ' + dListGML[0]
            bisemantics(lod3geometry, d0, "ClosureSurface")

def buildinginstallationSolid(skipsm, cs, kind, d, semantics=0, window=None, side=None, embrasure=None):
    """Generate the solid of a building installation."""
    dList, dListGML = d

    if semantics == 0:
        if kind == 'dormer':
            d1 = dListGML[0] + ' ' + dListGML[1] + ' ' + dListGML[4] + ' ' + dListGML[0]
            d2 = dListGML[0] + ' ' + dListGML[4] + ' ' + dListGML[5] + ' ' + dListGML[3] + ' ' + dListGML[0]
            d3 = dListGML[5] + ' ' + dListGML[2] + ' ' + dListGML[3] + ' ' + dListGML[5]
            addsurface(skipsm, cs, d1) 
            addsurface(skipsm, cs, d2) 
            addsurface(skipsm, cs, d3)

            #d4 = dListGML[4] + ' ' + dListGML[1] + ' ' + dListGML[2] + ' ' + dListGML[5] + ' ' + dListGML[4]
            #addsurface(skipsm, cs, d4)

            #-- Face with the window
            if embrasure is not None and embrasure > 0.0:

                d4 = dListGML[4] + ' ' + dListGML[1] + ' ' + dListGML[2] + ' ' + dListGML[5] + ' ' + dListGML[4]
                if side == 1:
                    dw = [[], [], [], []]
                    ew = [[], [], [], []]

                    dw[0] = [dList[4][0], dList[4][1] + window, dList[4][2] - window]
                    dw[1] = [dList[1][0], dList[1][1] + window, dList[1][2] + window]
                    dw[2] = [dList[2][0], dList[2][1] - window, dList[2][2] + window]
                    dw[3] = [dList[5][0], dList[5][1] - window, dList[5][2] - window]

                    ew[0] = [dList[4][0] - embrasure, dList[4][1] + window, dList[4][2] - window]
                    ew[1] = [dList[1][0] - embrasure, dList[1][1] + window, dList[1][2] + window]
                    ew[2] = [dList[2][0] - embrasure, dList[2][1] - window, dList[2][2] + window]
                    ew[3] = [dList[5][0] - embrasure, dList[5][1] - window, dList[5][2] - window]

                elif side == 3:
                    dw = [[], [], [], []]
                    ew = [[], [], [], []]

                    dw[0] = [dList[4][0], dList[4][1] - window, dList[4][2] - window]
                    dw[1] = [dList[1][0], dList[1][1] - window, dList[1][2] + window]
                    dw[2] = [dList[2][0], dList[2][1] + window, dList[2][2] + window]
                    dw[3] = [dList[5][0], dList[5][1] + window, dList[5][2] - window]

                    ew[0] = [dList[4][0] + embrasure, dList[4][1] - window, dList[4][2] - window]
                    ew[1] = [dList[1][0] + embrasure, dList[1][1] - window, dList[1][2] + window]
                    ew[2] = [dList[2][0] + embrasure, dList[2][1] + window, dList[2][2] + window]
                    ew[3] = [dList[5][0] + embrasure, dList[5][1] + window, dList[5][2] - window]

                elif side == 0:
                    dw = [[], [], [], []]
                    ew = [[], [], [], []]
                    dw[0] = [dList[4][0] + window, dList[4][1], dList[4][2] - window]
                    dw[1] = [dList[1][0] + window, dList[1][1], dList[1][2] + window]
                    dw[2] = [dList[2][0] - window, dList[2][1], dList[2][2] + window]
                    dw[3] = [dList[5][0] - window, dList[5][1], dList[5][2] - window]

                    ew[0] = [dList[4][0] + window, dList[4][1] + embrasure, dList[4][2] - window]
                    ew[1] = [dList[1][0] + window, dList[1][1] + embrasure, dList[1][2] + window]
                    ew[2] = [dList[2][0] - window, dList[2][1] + embrasure, dList[2][2] + window]
                    ew[3] = [dList[5][0] - window, dList[5][1] + embrasure, dList[5][2] - window]

                elif side == 2:
                    dw = [[], [], [], []]
                    ew = [[], [], [], []]

                    dw[0] = [dList[4][0] - window, dList[4][1], dList[4][2] - window]
                    dw[1] = [dList[1][0] - window, dList[1][1], dList[1][2] + window]
                    dw[2] = [dList[2][0] + window, dList[2][1], dList[2][2] + window]
                    dw[3] = [dList[5][0] + window, dList[5][1], dList[5][2] - window]

                    ew[0] = [dList[4][0] - window, dList[4][1] - embrasure, dList[4][2] - window]
                    ew[1] = [dList[1][0] - window, dList[1][1] - embrasure, dList[1][2] + window]
                    ew[2] = [dList[2][0] + window, dList[2][1] - embrasure, dList[2][2] + window]
                    ew[3] = [dList[5][0] + window, dList[5][1] - embrasure, dList[5][2] - window]      

                dwring = GMLPointList(dw[0]) + ' ' + GMLPointList(dw[3]) + ' ' + GMLPointList(dw[2]) + ' ' + GMLPointList(dw[1]) + ' ' + GMLPointList(dw[0])
                addsurface(skipsm, cs, d4, [dwring])


                dw0 = GMLPointList(dw[0]) + ' ' + GMLPointList(dw[1]) + ' ' + GMLPointList(ew[1]) + ' ' + GMLPointList(ew[0]) + ' ' + GMLPointList(dw[0])
                dw1 = GMLPointList(dw[1]) + ' ' + GMLPointList(dw[2]) + ' ' + GMLPointList(ew[2]) + ' ' + GMLPointList(ew[1]) + ' ' + GMLPointList(dw[1])
                dw2 = GMLPointList(dw[3]) + ' ' + GMLPointList(ew[3]) + ' ' + GMLPointList(ew[2]) + ' ' + GMLPointList(dw[2]) + ' ' + GMLPointList(dw[3])
                dw3 = GMLPointList(dw[3]) + ' ' + GMLPointList(dw[0]) + ' ' + GMLPointList(ew[0]) + ' ' + GMLPointList(ew[3]) + ' ' + GMLPointList(dw[3])

                ew0 = GMLPointList(ew[0]) + ' ' + GMLPointList(ew[1]) + ' ' + GMLPointList(ew[2]) + ' ' + GMLPointList(ew[3]) + ' ' + GMLPointList(ew[0])

                addsurface(skipsm, cs, dw0)
                addsurface(skipsm, cs, dw1)
                addsurface(skipsm, cs, dw2)
                addsurface(skipsm, cs, dw3)
                addsurface(skipsm, cs, ew0)

            else:
                d4 = dListGML[4] + ' ' + dListGML[1] + ' ' + dListGML[2] + ' ' + dListGML[5] + ' ' + dListGML[4]
                addsurface(skipsm, cs, d4)


def plainMultiSurface(surfaceMember, coords, interior=None):
    """Adds a polygon to the SurfaceMember."""
    Polygon = etree.SubElement(surfaceMember, "{%s}Polygon" % ns_gml)
    if ASSIGNID:
        Polygon.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
    PolygonExterior = etree.SubElement(Polygon, "{%s}exterior" % ns_gml)
    LinearRing = etree.SubElement(PolygonExterior, "{%s}LinearRing" % ns_gml)
    posList = etree.SubElement(LinearRing, "{%s}posList" % ns_gml)
    posList.text = coords

    if interior and interior[0] is not None:
        for hole in interior:
            PolygonInterior = etree.SubElement(Polygon, "{%s}interior" % ns_gml)
            LinearRing = etree.SubElement(PolygonInterior, "{%s}LinearRing" % ns_gml)
            posList = etree.SubElement(LinearRing, "{%s}posList" % ns_gml)
            posList.text = hole


def multiSurface(bldg, coords, semantics, interior=None, LOD=None, opening=None):
    """
    Write a surface with input coordinates.
    Input: coordinates of the LinearRing.
    Output: CompositeSurface.
    """
    boundedBy = etree.SubElement(bldg, "{%s}boundedBy" % ns_bldg)
    semanticSurface = etree.SubElement(boundedBy, "{%s}%s" % (ns_bldg, semantics))
    if LOD == 3:
        lodXMultiSurface = etree.SubElement(semanticSurface, "{%s}lod3MultiSurface" % ns_bldg)
    elif LOD == 2:
        lodXMultiSurface = etree.SubElement(semanticSurface, "{%s}lod2MultiSurface" % ns_bldg)
    else:
        lodXMultiSurface = etree.SubElement(semanticSurface, "{%s}lod2MultiSurface" % ns_bldg)
    MultiSurface = etree.SubElement(lodXMultiSurface, "{%s}MultiSurface" % ns_gml)
    surfaceMember = etree.SubElement(MultiSurface, "{%s}surfaceMember" % ns_gml)
    Polygon = etree.SubElement(surfaceMember, "{%s}Polygon" % ns_gml)
    if ASSIGNID:
        Polygon.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
    PolygonExterior = etree.SubElement(Polygon, "{%s}exterior" % ns_gml)
    LinearRing = etree.SubElement(PolygonExterior, "{%s}LinearRing" % ns_gml)
    posList = etree.SubElement(LinearRing, "{%s}posList" % ns_gml)
    posList.text = coords

    if interior and interior[0] is not None:
        for hole in interior:
            PolygonInterior = etree.SubElement(Polygon, "{%s}interior" % ns_gml)
            LinearRing = etree.SubElement(PolygonInterior, "{%s}LinearRing" % ns_gml)
            posList = etree.SubElement(LinearRing, "{%s}posList" % ns_gml)
            posList.text = hole

    if opening:

        dooropening = opening[0]

        if dooropening != []:
            gmlopening = etree.SubElement(semanticSurface, "{%s}opening" % ns_bldg)
            gmldoor = etree.SubElement(gmlopening, "{%s}Door" % ns_bldg)
            lod3MultiSurface = etree.SubElement(gmldoor, "{%s}lod3MultiSurface" % ns_bldg)
            DoorMultiSurface = etree.SubElement(lod3MultiSurface, "{%s}MultiSurface" % ns_gml)
            DoorsurfaceMember = etree.SubElement(DoorMultiSurface, "{%s}surfaceMember" % ns_gml)
            DoorPolygon = etree.SubElement(DoorsurfaceMember, "{%s}Polygon" % ns_gml)
            if ASSIGNID:
                DoorPolygon.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
            DoorPolygonExterior = etree.SubElement(DoorPolygon, "{%s}exterior" % ns_gml)
            DoorLinearRing = etree.SubElement(DoorPolygonExterior, "{%s}LinearRing" % ns_gml)
            DoorposList = etree.SubElement(DoorLinearRing, "{%s}posList" % ns_gml)
            DoorposList.text = GMLreversedRing(dooropening['ring'])

        if len(opening[1]) > 0:
            for win in opening[1]:
                #print win
                gmlopening = etree.SubElement(semanticSurface, "{%s}opening" % ns_bldg)
                gmlwin = etree.SubElement(gmlopening, "{%s}Window" % ns_bldg)
                lod3MultiSurface = etree.SubElement(gmlwin, "{%s}lod3MultiSurface" % ns_bldg)
                DoorMultiSurface = etree.SubElement(lod3MultiSurface, "{%s}MultiSurface" % ns_gml)
                DoorsurfaceMember = etree.SubElement(DoorMultiSurface, "{%s}surfaceMember" % ns_gml)
                DoorPolygon = etree.SubElement(DoorsurfaceMember, "{%s}Polygon" % ns_gml)
                if ASSIGNID:
                    DoorPolygon.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
                DoorPolygonExterior = etree.SubElement(DoorPolygon, "{%s}exterior" % ns_gml)
                DoorLinearRing = etree.SubElement(DoorPolygonExterior, "{%s}LinearRing" % ns_gml)
                DoorposList = etree.SubElement(DoorLinearRing, "{%s}posList" % ns_gml)
                DoorposList.text = GMLreversedRing(win['ring'])

def multiSurface2(bldg, coords, semantics, interior=None, LOD=None, window=None):
    """
    Write a surface with input coordinates.
    Input: coordinates of the LinearRing.
    Output: MultiSurface.
    """
    boundedBy = etree.SubElement(bldg, "{%s}boundedBy" % ns_bldg)
    semanticSurface = etree.SubElement(boundedBy, "{%s}%s" % (ns_bldg, semantics))
    if LOD == 3:
        lodXMultiSurface = etree.SubElement(semanticSurface, "{%s}lod3MultiSurface" % ns_bldg)
    elif LOD == 2:
        lodXMultiSurface = etree.SubElement(semanticSurface, "{%s}lod2MultiSurface" % ns_bldg)
    else:
        lodXMultiSurface = etree.SubElement(semanticSurface, "{%s}lod2MultiSurface" % ns_bldg)
    MultiSurface = etree.SubElement(lodXMultiSurface, "{%s}MultiSurface" % ns_gml)
    surfaceMember = etree.SubElement(MultiSurface, "{%s}surfaceMember" % ns_gml)
    Polygon = etree.SubElement(surfaceMember, "{%s}Polygon" % ns_gml)
    if ASSIGNID:
        Polygon.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
    PolygonExterior = etree.SubElement(Polygon, "{%s}exterior" % ns_gml)
    LinearRing = etree.SubElement(PolygonExterior, "{%s}LinearRing" % ns_gml)
    posList = etree.SubElement(LinearRing, "{%s}posList" % ns_gml)
    posList.text = coords

    if interior and interior[0] is not None:
        for hole in interior:
            PolygonInterior = etree.SubElement(Polygon, "{%s}interior" % ns_gml)
            LinearRing = etree.SubElement(PolygonInterior, "{%s}LinearRing" % ns_gml)
            posList = etree.SubElement(LinearRing, "{%s}posList" % ns_gml)
            posList.text = hole

    if window:
        if len(window) > 0:
            for win in window:
                #print win
                gmlopening = etree.SubElement(semanticSurface, "{%s}opening" % ns_bldg)
                gmlwin = etree.SubElement(gmlopening, "{%s}Window" % ns_bldg)
                lod3MultiSurface = etree.SubElement(gmlwin, "{%s}lod3MultiSurface" % ns_bldg)
                DoorMultiSurface = etree.SubElement(lod3MultiSurface, "{%s}MultiSurface" % ns_gml)
                DoorsurfaceMember = etree.SubElement(DoorMultiSurface, "{%s}surfaceMember" % ns_gml)
                DoorPolygon = etree.SubElement(DoorsurfaceMember, "{%s}Polygon" % ns_gml)
                if ASSIGNID:
                    DoorPolygon.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
                DoorPolygonExterior = etree.SubElement(DoorPolygon, "{%s}exterior" % ns_gml)
                DoorLinearRing = etree.SubElement(DoorPolygonExterior, "{%s}LinearRing" % ns_gml)
                DoorposList = etree.SubElement(DoorLinearRing, "{%s}posList" % ns_gml)
                DoorposList.text = win


def multiSurfaceWithEmbrasure(bldg, coords, semantics, interior=None, LOD=None, embO=None):
    """
    Write a surface with input coordinates, taking into account the embrasures.
    Input: coordinates of the LinearRing.
    Output: CompositeSurface.
    """
    boundedBy = etree.SubElement(bldg, "{%s}boundedBy" % ns_bldg)
    semanticSurface = etree.SubElement(boundedBy, "{%s}%s" % (ns_bldg, semantics))
    if LOD == 3:
        lodXMultiSurface = etree.SubElement(semanticSurface, "{%s}lod3MultiSurface" % ns_bldg)
    elif LOD == 2:
        lodXMultiSurface = etree.SubElement(semanticSurface, "{%s}lod2MultiSurface" % ns_bldg)
    else:
        lodXMultiSurface = etree.SubElement(semanticSurface, "{%s}lod2MultiSurface" % ns_bldg)
    MultiSurface = etree.SubElement(lodXMultiSurface, "{%s}MultiSurface" % ns_gml)
    surfaceMember = etree.SubElement(MultiSurface, "{%s}surfaceMember" % ns_gml)
    Polygon = etree.SubElement(surfaceMember, "{%s}Polygon" % ns_gml)
    if ASSIGNID:
        Polygon.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
    PolygonExterior = etree.SubElement(Polygon, "{%s}exterior" % ns_gml)
    LinearRing = etree.SubElement(PolygonExterior, "{%s}LinearRing" % ns_gml)
    posList = etree.SubElement(LinearRing, "{%s}posList" % ns_gml)
    posList.text = coords

    if interior and interior[0] is not None:
        for hole in interior:
            PolygonInterior = etree.SubElement(Polygon, "{%s}interior" % ns_gml)
            LinearRing = etree.SubElement(PolygonInterior, "{%s}LinearRing" % ns_gml)
            posList = etree.SubElement(LinearRing, "{%s}posList" % ns_gml)
            posList.text = hole

    for opening in embO:
        for s in opening['surfaces']:
            # MultiSurface = etree.SubElement(lodXMultiSurface, "{%s}MultiSurface" % ns_gml)
            surfaceMember = etree.SubElement(MultiSurface, "{%s}surfaceMember" % ns_gml)
            Polygon = etree.SubElement(surfaceMember, "{%s}Polygon" % ns_gml)
            if ASSIGNID:
                Polygon.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
            PolygonExterior = etree.SubElement(Polygon, "{%s}exterior" % ns_gml)
            LinearRing = etree.SubElement(PolygonExterior, "{%s}LinearRing" % ns_gml)
            posList = etree.SubElement(LinearRing, "{%s}posList" % ns_gml)
            posList.text = s
        for o in opening['openings']:
            gmlopening = etree.SubElement(semanticSurface, "{%s}opening" % ns_bldg)
            if opening['type'] == 'Door':
                gmldoor = etree.SubElement(gmlopening, "{%s}Door" % ns_bldg)
            elif opening['type'] == 'Window':
                gmldoor = etree.SubElement(gmlopening, "{%s}Window" % ns_bldg)
            else:
                raise ValueError("Door or window allowed.")
            lod3MultiSurface = etree.SubElement(gmldoor, "{%s}lod3MultiSurface" % ns_bldg)
            DoorMultiSurface = etree.SubElement(lod3MultiSurface, "{%s}MultiSurface" % ns_gml)
            DoorsurfaceMember = etree.SubElement(DoorMultiSurface, "{%s}surfaceMember" % ns_gml)
            DoorPolygon = etree.SubElement(DoorsurfaceMember, "{%s}Polygon" % ns_gml)
            if ASSIGNID:
                DoorPolygon.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
            DoorPolygonExterior = etree.SubElement(DoorPolygon, "{%s}exterior" % ns_gml)
            DoorLinearRing = etree.SubElement(DoorPolygonExterior, "{%s}LinearRing" % ns_gml)
            DoorposList = etree.SubElement(DoorLinearRing, "{%s}posList" % ns_gml)
            DoorposList.text = o#['ring']


def multiSurfaceLOD0(bldg, coords, footedge):
    """
    Write a surface with input coordinates.
    Input: coordinates of the LinearRing.
    Output: MultiSurface.
    """
    if footedge == "footprint":
        lod0MultiSurface = etree.SubElement(bldg, "{%s}lod0FootPrint" % ns_bldg)
    elif footedge == "roofedge":
        lod0MultiSurface = etree.SubElement(bldg, "{%s}lod0RoofEdge" % ns_bldg)
    MultiSurface = etree.SubElement(lod0MultiSurface, "{%s}MultiSurface" % ns_gml)
    surfaceMember = etree.SubElement(MultiSurface, "{%s}surfaceMember" % ns_gml)
    Polygon = etree.SubElement(surfaceMember, "{%s}Polygon" % ns_gml)
    if ASSIGNID:
        Polygon.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
    PolygonExterior = etree.SubElement(Polygon, "{%s}exterior" % ns_gml)
    LinearRing = etree.SubElement(PolygonExterior, "{%s}LinearRing" % ns_gml)
    posList = etree.SubElement(LinearRing, "{%s}posList" % ns_gml)
    posList.text = coords


def CityGMLbuildingLOD0(CityModel, ID, attributes, o, x, y, z, h=None, rtype=None, top=None, override=None, LOD=None, aux=None, buildingpart=None, fd=False):
    """
    Generate a cityObjectMember representing a building in LOD0.
    Output: CityGML code of the cityObjectMember.
    """
    cityObject = etree.SubElement(CityModel, "cityObjectMember")
    bldg = etree.SubElement(cityObject, "{%s}Building" % ns_bldg)
    bldg.attrib['{%s}id' % ns_gml] = ID
    roofType = etree.SubElement(bldg, "{%s}roofType" % ns_bldg)
    roofType.text = rtype

    yearOfConstructionXML = etree.SubElement(bldg, "{%s}yearOfConstruction" % ns_bldg)
    yearOfConstructionXML.text = attributes['yearOfConstruction']
    functionXML = etree.SubElement(bldg, "{%s}function" % ns_bldg)
    functionXML.text = attributes['function']
    storeysAboveGroundXML = etree.SubElement(bldg, "{%s}storeysAboveGround" % ns_bldg)
    storeysAboveGroundXML.text = attributes['storeysAboveGround']
    storeysAboveGroundXML = etree.SubElement(bldg, "{%s}storeysAboveGround" % ns_bldg)
    storeysAboveGroundXML.text = attributes['storeysAboveGround']

    if top is not None:
        if top == 1.0 and rtype == 'Shed':
            p = verticesBody(o, x, y, z, h, None, override)
        else:
            p = verticesBody(o, x, y, z, h, top)
    elif top is None:
        p = verticesBody(o, x, y, z, h, None, override)

    #-- Is the building part covered by overhangs?
    if buildingpart is not None:
        if x > aux['xsize'] and aux['ovhx'] >= buildingpart['x']:
            covered = True
        else:
            covered = False
    else:
        covered = None

    footprints = []
    roofedges = []


    #-- Account for building parts
    if buildingpart is not None and not covered:

        #-- Accounting for overhangs
        if x > aux['xsize']:# or x < aux['xsize']:
            bp = [None] * 8
            bp[0] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[1] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[2] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[3] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[4] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])
            bp[7] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])

            #-- Top with the rest of the building
            bpT = [None] * 8
            tH = GMLstring2points(p[4])[0][2]
            bpT[4] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'], tH])
            bpT[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], tH])
            bpT[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])
            bpT[7] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])
 
        elif fd and x < aux['xsize']:

            bp = [None] * 8
            eastline = GMLstring2points(p[1])[0][0]
            bp[0] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[1] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[2] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[3] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[4] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])
            bp[7] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])

            #-- Top with the rest of the building
            bpT = [None] * 8
            tH = GMLstring2points(p[4])[0][2]
            bpT[4] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'], tH])
            bpT[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], tH])
            bpT[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])
            bpT[7] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])

        else:
            bp = [None] * 8
            bp[0] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[1] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[2] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[3] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[4] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[5] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[6] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])
            bp[7] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])

            #-- Top with the rest of the building
            bpT = [None] * 8
            tH = GMLstring2points(p[4])[0][2]
            bpT[4] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'], tH])
            bpT[5] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'], tH])
            bpT[6] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])
            bpT[7] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])

        if buildingpart['type'] == 'Alcove':
            if LOD == '0.1':
                faceBottom = "%s %s %s %s %s" % (p[0], p[3], p[2], p[1], p[0])
                footprints.append(faceBottom)
                #faceTop = "%s %s %s %s %s" % (p[4], p[5], p[6], p[7], p[4])
                #roofedges.append(faceTop)
            elif LOD == '0.2':
                faceBottom = "%s %s %s %s %s %s %s %s %s" % (p[0], p[3], p[2], bp[3], bp[2], bp[1], bp[0], p[1], p[0])
                footprints.append(faceBottom)
                faceTop = "%s %s %s %s %s %s %s %s %s" % (p[4], p[5], bpT[4], bpT[5], bpT[6], bpT[7], p[6], p[7], p[4])
                roofedges.append(faceTop)    
            elif LOD == '0.3':
                faceBottom = "%s %s %s %s %s %s %s %s %s" % (p[0], p[3], p[2], bp[3], bp[2], bp[1], bp[0], p[1], p[0])
                footprints.append(faceBottom)
                faceTop = "%s %s %s %s %s" % (p[4], p[5], p[6], p[7], p[4])
                roofedges.append(faceTop)
                gtop = "%s %s %s %s %s" % (bp[4], bp[5], bp[6], bp[7], bp[4])
                roofedges.append(gtop)                         
        elif buildingpart['type'] == 'Garage':
            if LOD == '0.1' or LOD == '0.2' or LOD == '0.3':
                faceBottom = "%s %s %s %s %s %s %s %s %s" % (p[0], p[3], p[2], bp[3], bp[2], bp[1], bp[0], p[1], p[0])
                footprints.append(faceBottom)
                if LOD == '0.2':
                    faceTop = "%s %s %s %s %s %s %s %s %s" % (p[4], p[5], bpT[4], bpT[5], bpT[6], bpT[7], p[6], p[7], p[4])
                    roofedges.append(faceTop)
                elif LOD == '0.3':
                    faceTop = "%s %s %s %s %s" % (p[4], p[5], p[6], p[7], p[4])
                    roofedges.append(faceTop)
                    gtop = "%s %s %s %s %s" % (bp[4], bp[5], bp[6], bp[7], bp[4])
                    roofedges.append(gtop)
    else:
        footprint = "%s %s %s %s %s" % (p[0], p[3], p[2], p[1], p[0])
        footprints.append(footprint)
        if LOD == '0.2' or LOD == '0.3':
            faceTop = "%s %s %s %s %s" % (p[4], p[5], p[6], p[7], p[4])
            roofedges.append(faceTop)


    #-- Bottom face
    for ft in footprints:
        multiSurfaceLOD0(bldg, GMLreversedRing(ft), "footprint")

    #-- Top face
    for re in roofedges:
        multiSurfaceLOD0(bldg, re, "roofedge")


def CityGMLbuildingLOD1(CityModel, ID, attributes, o, x, y, z, h=None, rtype=None, top=None, override=None, LOD=None, aux=None, buildingpart=None, fd=False):
    """
    Generate a cityObjectMember representing a building in LOD1.
    Input: ID, origin, width, depth, height, and optionally: height of the roof, roof type, block model top modelling rule, walls modelling rule.
    Output: CityGML code of the cityObjectMember.
    """
    cityObject = etree.SubElement(CityModel, "cityObjectMember")
    bldg = etree.SubElement(cityObject, "{%s}Building" % ns_bldg)
    bldg.attrib['{%s}id' % ns_gml] = ID
    roofType = etree.SubElement(bldg, "{%s}roofType" % ns_bldg)
    roofType.text = rtype

    yearOfConstructionXML = etree.SubElement(bldg, "{%s}yearOfConstruction" % ns_bldg)
    yearOfConstructionXML.text = attributes['yearOfConstruction']
    functionXML = etree.SubElement(bldg, "{%s}function" % ns_bldg)
    functionXML.text = attributes['function']
    storeysAboveGroundXML = etree.SubElement(bldg, "{%s}storeysAboveGround" % ns_bldg)
    storeysAboveGroundXML.text = attributes['storeysAboveGround']

    if top is not None:
        if top == 1.0 and rtype == 'Shed':
            p = verticesBody(o, x, y, z, h, None, override)
        else:
            p = verticesBody(o, x, y, z, h, top)
    elif top is None:
        p = verticesBody(o, x, y, z, h, None, override)

    lod1MultiSurface = etree.SubElement(bldg, "{%s}lod1MultiSurface" % ns_bldg)
    MultiSurface = etree.SubElement(lod1MultiSurface, "{%s}MultiSurface" % ns_gml)
    surfaceMember = etree.SubElement(MultiSurface, "{%s}surfaceMember" % ns_gml)
    

    faces = []
    face0 = "%s %s %s %s %s" % (p[0], p[1], p[5], p[4], p[0])
    faces.append(face0)
    face2 = "%s %s %s %s %s" % (p[2], p[3], p[7], p[6], p[2])
    faces.append(face2)
    face3 = "%s %s %s %s %s" % (p[3], p[0], p[4], p[7], p[3])
    faces.append(face3)

    #-- Is the building part covered by overhangs?
    if buildingpart is not None:
        if x > aux['xsize'] and aux['ovhx'] >= buildingpart['x']:
            covered = True
        else:
            covered = False
    else:
        covered = None

    #-- Account for building parts
    if buildingpart is not None and not covered:

        #-- Accounting for overhangs
        if x > aux['xsize']:# or x < aux['xsize']:
            bp = [None] * 8
            bp[0] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[1] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[2] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[3] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[4] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])
            bp[7] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])

            #-- Top with the rest of the building
            bpT = [None] * 8
            tH = GMLstring2points(p[4])[0][2]
            bpT[4] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'], tH])
            bpT[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], tH])
            bpT[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])
            bpT[7] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])

        elif fd and x < aux['xsize']:

            bp = [None] * 8
            eastline = GMLstring2points(p[1])[0][0]
            bp[0] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[1] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[2] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[3] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[4] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])
            bp[7] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])

            #-- Top with the rest of the building
            bpT = [None] * 8
            tH = GMLstring2points(p[4])[0][2]
            bpT[4] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'], tH])
            bpT[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], tH])
            bpT[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])
            bpT[7] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])


        else:
            bp = [None] * 8
            bp[0] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[1] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[2] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[3] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[4] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[5] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[6] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])
            bp[7] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])

            #-- Top with the rest of the building
            bpT = [None] * 8
            tH = GMLstring2points(p[4])[0][2]
            bpT[4] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'], tH])
            bpT[5] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'], tH])
            bpT[6] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])
            bpT[7] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])

        if buildingpart['type'] == 'Alcove':
            if LOD == '1.1':
                face1 = "%s %s %s %s %s" % (p[1], p[2], p[6], p[5], p[1])
                faces.append(face1)
                faceBottom = "%s %s %s %s %s" % (p[0], p[3], p[2], p[1], p[0])
                faces.append(faceBottom)
                faceTop = "%s %s %s %s %s" % (p[4], p[5], p[6], p[7], p[4])
                faces.append(faceTop)
            elif LOD == '1.2':
                faceBottom = "%s %s %s %s %s %s %s %s %s" % (p[0], p[3], p[2], bp[3], bp[2], bp[1], bp[0], p[1], p[0])
                faces.append(faceBottom)
                faceTop = "%s %s %s %s %s %s %s %s %s" % (p[4], p[5], bpT[4], bpT[5], bpT[6], bpT[7], p[6], p[7], p[4])
                faces.append(faceTop)
                face1_0 = "%s %s %s %s %s" % (p[1], bp[0], bpT[4], p[5], p[1])
                faces.append(face1_0)
                face1_1 = "%s %s %s %s %s" % (p[2], p[6], bpT[7], bp[3], p[2])
                faces.append(face1_1)
                gface0 = "%s %s %s %s %s" % (bp[0], bp[1], bpT[5], bpT[4], bp[0])
                faces.append(gface0)
                gface1 = "%s %s %s %s %s" % (bp[1], bp[2], bpT[6], bpT[5], bp[1])
                faces.append(gface1)
                gface3 = "%s %s %s %s %s" % (bp[3], bpT[7], bpT[6], bp[2], bp[3])
                faces.append(gface3)
            elif LOD == '1.3':
                faceBottom = "%s %s %s %s %s %s %s %s %s" % (p[0], p[3], p[2], bp[3], bp[2], bp[1], bp[0], p[1], p[0])
                faces.append(faceBottom)
                faceTop = "%s %s %s %s %s" % (p[4], p[5], p[6], p[7], p[4])
                faces.append(faceTop)
                face1 = "%s %s %s %s %s %s %s %s %s" % (p[1], bp[0], bp[4], bp[7], bp[3], p[2], p[6], p[5], p[1])
                faces.append(face1)
                gface0 = "%s %s %s %s %s" % (bp[0], bp[1], bp[5], bp[4], bp[0])
                faces.append(gface0)
                gface1 = "%s %s %s %s %s" % (bp[1], bp[2], bp[6], bp[5], bp[1])
                faces.append(gface1)
                gface3 = "%s %s %s %s %s" % (bp[3], bp[7], bp[6], bp[2], bp[3])
                faces.append(gface3)
                gtop = "%s %s %s %s %s" % (bp[4], bp[5], bp[6], bp[7], bp[4])
                faces.append(gtop)                
        elif buildingpart['type'] == 'Garage':
            if LOD == '1.1' or LOD == '1.2' or LOD == '1.3':
                faceBottom = "%s %s %s %s %s %s %s %s %s" % (p[0], p[3], p[2], bp[3], bp[2], bp[1], bp[0], p[1], p[0])
                faces.append(faceBottom)
                if LOD == '1.1' or LOD == '1.2':
                    faceTop = "%s %s %s %s %s %s %s %s %s" % (p[4], p[5], bpT[4], bpT[5], bpT[6], bpT[7], p[6], p[7], p[4])
                    faces.append(faceTop)
                    face1_0 = "%s %s %s %s %s" % (p[1], bp[0], bpT[4], p[5], p[1])
                    faces.append(face1_0)
                    face1_1 = "%s %s %s %s %s" % (p[2], p[6], bpT[7], bp[3], p[2])
                    faces.append(face1_1)
                    gface0 = "%s %s %s %s %s" % (bp[0], bp[1], bpT[5], bpT[4], bp[0])
                    faces.append(gface0)
                    gface1 = "%s %s %s %s %s" % (bp[1], bp[2], bpT[6], bpT[5], bp[1])
                    faces.append(gface1)
                    gface3 = "%s %s %s %s %s" % (bp[3], bpT[7], bpT[6], bp[2], bp[3])
                    faces.append(gface3)
                elif LOD == '1.3':
                    faceTop = "%s %s %s %s %s" % (p[4], p[5], p[6], p[7], p[4])
                    faces.append(faceTop)
                    face1 = "%s %s %s %s %s %s %s %s %s" % (p[1], bp[0], bp[4], bp[7], bp[3], p[2], p[6], p[5], p[1])
                    faces.append(face1)
                    gface0 = "%s %s %s %s %s" % (bp[0], bp[1], bp[5], bp[4], bp[0])
                    faces.append(gface0)
                    gface1 = "%s %s %s %s %s" % (bp[1], bp[2], bp[6], bp[5], bp[1])
                    faces.append(gface1)
                    gface3 = "%s %s %s %s %s" % (bp[3], bp[7], bp[6], bp[2], bp[3])
                    faces.append(gface3)
                    gtop = "%s %s %s %s %s" % (bp[4], bp[5], bp[6], bp[7], bp[4])
                    faces.append(gtop)
    else:
        face1 = "%s %s %s %s %s" % (p[1], p[2], p[6], p[5], p[1])
        faces.append(face1)
        faceBottom = "%s %s %s %s %s" % (p[0], p[3], p[2], p[1], p[0])
        faces.append(faceBottom)
        faceTop = "%s %s %s %s %s" % (p[4], p[5], p[6], p[7], p[4])
        faces.append(faceTop)

    for face in faces:
        plainMultiSurface(surfaceMember, face)


def CityGMLbuildingLOD1Semantics(CityModel, ID, attributes, o, x, y, z, h=None, rtype=None, top=None, override=None, LOD=None, aux=None, buildingpart=None, fd=False):
    """
    Generate a cityObjectMember representing a building in a special experimental form of LOD1 currently not really supported by the standard.
    Input: ID, origin, width, depth, height, and optionally: height of the roof, roof type, block model top modelling rule, walls modelling rule.
    Output: CityGML code of the cityObjectMember.
    """
    cityObject = etree.SubElement(CityModel, "cityObjectMember")
    bldg = etree.SubElement(cityObject, "{%s}Building" % ns_bldg)
    bldg.attrib['{%s}id' % ns_gml] = ID
    roofType = etree.SubElement(bldg, "{%s}roofType" % ns_bldg)
    roofType.text = rtype

    yearOfConstructionXML = etree.SubElement(bldg, "{%s}yearOfConstruction" % ns_bldg)
    yearOfConstructionXML.text = attributes['yearOfConstruction']
    functionXML = etree.SubElement(bldg, "{%s}function" % ns_bldg)
    functionXML.text = attributes['function']
    storeysAboveGroundXML = etree.SubElement(bldg, "{%s}storeysAboveGround" % ns_bldg)
    storeysAboveGroundXML.text = attributes['storeysAboveGround']

    if top is not None:
        if top == 1.0 and rtype == 'Shed':
            p = verticesBody(o, x, y, z, h, None, override)
        else:
            p = verticesBody(o, x, y, z, h, top)
    elif top is None:
        p = verticesBody(o, x, y, z, h, None, override)

    Wfaces = []
    Rfaces = []
    Gfaces = []

    face0 = "%s %s %s %s %s" % (p[0], p[1], p[5], p[4], p[0])
    Wfaces.append(face0)
    face2 = "%s %s %s %s %s" % (p[2], p[3], p[7], p[6], p[2])
    Wfaces.append(face2)
    face3 = "%s %s %s %s %s" % (p[3], p[0], p[4], p[7], p[3])
    Wfaces.append(face3)

    #-- Is the building part covered by overhangs?
    if buildingpart is not None:
        if x > aux['xsize'] and aux['ovhx'] >= buildingpart['x']:
            covered = True
        else:
            covered = False
    else:
        covered = None

    #-- Account for building parts
    if buildingpart is not None and not covered:

        #-- Accounting for overhangs
        if x > aux['xsize']:# or x < aux['xsize']:
            bp = [None] * 8
            bp[0] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[1] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[2] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[3] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[4] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])
            bp[7] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])

            #-- Top with the rest of the building
            bpT = [None] * 8
            tH = GMLstring2points(p[4])[0][2]
            bpT[4] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'], tH])
            bpT[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], tH])
            bpT[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])
            bpT[7] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])

        elif fd and x < aux['xsize']:

            bp = [None] * 8
            eastline = GMLstring2points(p[1])[0][0]
            bp[0] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[1] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[2] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[3] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[4] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])
            bp[7] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])

            #-- Top with the rest of the building
            bpT = [None] * 8
            tH = GMLstring2points(p[4])[0][2]
            bpT[4] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'], tH])
            bpT[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], tH])
            bpT[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])
            bpT[7] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])


        else:
            bp = [None] * 8
            bp[0] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[1] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[2] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[3] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[4] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[5] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[6] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])
            bp[7] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])

            #-- Top with the rest of the building
            bpT = [None] * 8
            tH = GMLstring2points(p[4])[0][2]
            bpT[4] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'], tH])
            bpT[5] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'], tH])
            bpT[6] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])
            bpT[7] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])

        if buildingpart['type'] == 'Alcove':
            if LOD == '1.1':
                face1 = "%s %s %s %s %s" % (p[1], p[2], p[6], p[5], p[1])
                Wfaces.append(face1)
                faceBottom = "%s %s %s %s %s" % (p[0], p[3], p[2], p[1], p[0])
                Gfaces.append(faceBottom)
                faceTop = "%s %s %s %s %s" % (p[4], p[5], p[6], p[7], p[4])
                Rfaces.append(faceTop)
            elif LOD == '1.2':
                faceBottom = "%s %s %s %s %s %s %s %s %s" % (p[0], p[3], p[2], bp[3], bp[2], bp[1], bp[0], p[1], p[0])
                Gfaces.append(faceBottom)
                faceTop = "%s %s %s %s %s %s %s %s %s" % (p[4], p[5], bpT[4], bpT[5], bpT[6], bpT[7], p[6], p[7], p[4])
                Rfaces.append(faceTop)
                face1_0 = "%s %s %s %s %s" % (p[1], bp[0], bpT[4], p[5], p[1])
                Wfaces.append(face1_0)
                face1_1 = "%s %s %s %s %s" % (p[2], p[6], bpT[7], bp[3], p[2])
                Wfaces.append(face1_1)
                gface0 = "%s %s %s %s %s" % (bp[0], bp[1], bpT[5], bpT[4], bp[0])
                Wfaces.append(gface0)
                gface1 = "%s %s %s %s %s" % (bp[1], bp[2], bpT[6], bpT[5], bp[1])
                Wfaces.append(gface1)
                gface3 = "%s %s %s %s %s" % (bp[3], bpT[7], bpT[6], bp[2], bp[3])
                Wfaces.append(gface3)
            elif LOD == '1.3':
                faceBottom = "%s %s %s %s %s %s %s %s %s" % (p[0], p[3], p[2], bp[3], bp[2], bp[1], bp[0], p[1], p[0])
                Gfaces.append(faceBottom)
                faceTop = "%s %s %s %s %s" % (p[4], p[5], p[6], p[7], p[4])
                Rfaces.append(faceTop)
                face1 = "%s %s %s %s %s %s %s %s %s" % (p[1], bp[0], bp[4], bp[7], bp[3], p[2], p[6], p[5], p[1])
                Wfaces.append(face1)
                gface0 = "%s %s %s %s %s" % (bp[0], bp[1], bp[5], bp[4], bp[0])
                Wfaces.append(gface0)
                gface1 = "%s %s %s %s %s" % (bp[1], bp[2], bp[6], bp[5], bp[1])
                Wfaces.append(gface1)
                gface3 = "%s %s %s %s %s" % (bp[3], bp[7], bp[6], bp[2], bp[3])
                Wfaces.append(gface3)
                gtop = "%s %s %s %s %s" % (bp[4], bp[5], bp[6], bp[7], bp[4])
                Rfaces.append(gtop)                
        elif buildingpart['type'] == 'Garage':
            if LOD == '1.1' or LOD == '1.2' or LOD == '1.3':
                faceBottom = "%s %s %s %s %s %s %s %s %s" % (p[0], p[3], p[2], bp[3], bp[2], bp[1], bp[0], p[1], p[0])
                Gfaces.append(faceBottom)
                if LOD == '1.1' or LOD == '1.2':
                    faceTop = "%s %s %s %s %s %s %s %s %s" % (p[4], p[5], bpT[4], bpT[5], bpT[6], bpT[7], p[6], p[7], p[4])
                    Rfaces.append(faceTop)
                    face1_0 = "%s %s %s %s %s" % (p[1], bp[0], bpT[4], p[5], p[1])
                    Wfaces.append(face1_0)
                    face1_1 = "%s %s %s %s %s" % (p[2], p[6], bpT[7], bp[3], p[2])
                    Wfaces.append(face1_1)
                    gface0 = "%s %s %s %s %s" % (bp[0], bp[1], bpT[5], bpT[4], bp[0])
                    Wfaces.append(gface0)
                    gface1 = "%s %s %s %s %s" % (bp[1], bp[2], bpT[6], bpT[5], bp[1])
                    Wfaces.append(gface1)
                    gface3 = "%s %s %s %s %s" % (bp[3], bpT[7], bpT[6], bp[2], bp[3])
                    Wfaces.append(gface3)
                elif LOD == '1.3':
                    faceTop = "%s %s %s %s %s" % (p[4], p[5], p[6], p[7], p[4])
                    Rfaces.append(faceTop)
                    face1 = "%s %s %s %s %s %s %s %s %s" % (p[1], bp[0], bp[4], bp[7], bp[3], p[2], p[6], p[5], p[1])
                    Wfaces.append(face1)
                    gface0 = "%s %s %s %s %s" % (bp[0], bp[1], bp[5], bp[4], bp[0])
                    Wfaces.append(gface0)
                    gface1 = "%s %s %s %s %s" % (bp[1], bp[2], bp[6], bp[5], bp[1])
                    Wfaces.append(gface1)
                    gface3 = "%s %s %s %s %s" % (bp[3], bp[7], bp[6], bp[2], bp[3])
                    Wfaces.append(gface3)
                    gtop = "%s %s %s %s %s" % (bp[4], bp[5], bp[6], bp[7], bp[4])
                    Rfaces.append(gtop)
    else:
        face1 = "%s %s %s %s %s" % (p[1], p[2], p[6], p[5], p[1])
        Wfaces.append(face1)
        faceBottom = "%s %s %s %s %s" % (p[0], p[3], p[2], p[1], p[0])
        Gfaces.append(faceBottom)
        faceTop = "%s %s %s %s %s" % (p[4], p[5], p[6], p[7], p[4])
        Rfaces.append(faceTop)

    for face in Wfaces:
        multiSurface(bldg, face, "WallSurface", None)
    for face in Gfaces:
        multiSurface(bldg, face, "GroundSurface", None)
    for face in Rfaces:
        multiSurface(bldg, face, "RoofSurface", None)


def CityGMLbuildingLOD1Solid(CityModel, ID, attributes, o, x, y, z, h=None, rtype=None, top=None, override=None, LOD=None, aux=None, buildingpart=None, fd=False):
    """
    Generate a cityObjectMember representing a building as an LOD1 solid.
    Input: ID, origin, width, depth, height, and optionally: height of the roof, roof type, block model top modelling rule, walls modelling rule.
    Output: CityGML code of the cityObjectMember.
    """
    cityObject = etree.SubElement(CityModel, "cityObjectMember")
    bldg = etree.SubElement(cityObject, "{%s}Building" % ns_bldg)
    bldg.attrib['{%s}id' % ns_gml] = ID
    roofType = etree.SubElement(bldg, "{%s}roofType" % ns_bldg)
    roofType.text = rtype

    yearOfConstructionXML = etree.SubElement(bldg, "{%s}yearOfConstruction" % ns_bldg)
    yearOfConstructionXML.text = attributes['yearOfConstruction']
    functionXML = etree.SubElement(bldg, "{%s}function" % ns_bldg)
    functionXML.text = attributes['function']
    storeysAboveGroundXML = etree.SubElement(bldg, "{%s}storeysAboveGround" % ns_bldg)
    storeysAboveGroundXML.text = attributes['storeysAboveGround']

    if top is not None:
        if top == 1.0 and rtype == 'Shed':
            p = verticesBody(o, x, y, z, h, None, override)
        else:
            p = verticesBody(o, x, y, z, h, top)
    elif top is None:
        p = verticesBody(o, x, y, z, h, None, override)

    lod1Solid = etree.SubElement(bldg, "{%s}lod1Solid" % ns_bldg)
    Solid = etree.SubElement(lod1Solid, "{%s}Solid" % ns_gml)
    if ASSIGNID:
        Solid.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
    exterior = etree.SubElement(Solid, "{%s}exterior" % ns_gml)
    CompositeSurface = etree.SubElement(exterior, "{%s}CompositeSurface" % ns_gml)

    faces = []
    face0 = "%s %s %s %s %s" % (p[0], p[1], p[5], p[4], p[0])
    faces.append(face0)
    face2 = "%s %s %s %s %s" % (p[2], p[3], p[7], p[6], p[2])
    faces.append(face2)
    face3 = "%s %s %s %s %s" % (p[3], p[0], p[4], p[7], p[3])
    faces.append(face3)

    #-- Is the building part covered by overhangs?
    if buildingpart is not None:
        if x > aux['xsize'] and aux['ovhx'] >= buildingpart['x']:
            covered = True
        else:
            covered = False
    else:
        covered = None

    #-- Account for building parts
    if buildingpart is not None and not covered:

        #-- Accounting for overhangs
        if x > aux['xsize']:# or x < aux['xsize']:
            bp = [None] * 8
            bp[0] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[1] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[2] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[3] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[4] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])
            bp[7] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])

            #-- Top with the rest of the building
            bpT = [None] * 8
            tH = GMLstring2points(p[4])[0][2]
            bpT[4] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'], tH])
            bpT[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], tH])
            bpT[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])
            bpT[7] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])

        elif fd and x < aux['xsize']:

            bp = [None] * 8
            eastline = GMLstring2points(p[1])[0][0]
            bp[0] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[1] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[2] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[3] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[4] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])
            bp[7] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])

            #-- Top with the rest of the building
            bpT = [None] * 8
            tH = GMLstring2points(p[4])[0][2]
            bpT[4] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'], tH])
            bpT[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], tH])
            bpT[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])
            bpT[7] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])


        else:
            bp = [None] * 8
            bp[0] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[1] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[2] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[3] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[4] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[5] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[6] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])
            bp[7] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])

            #-- Top with the rest of the building
            bpT = [None] * 8
            tH = GMLstring2points(p[4])[0][2]
            bpT[4] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'], tH])
            bpT[5] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'], tH])
            bpT[6] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])
            bpT[7] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])

        if buildingpart['type'] == 'Alcove':
            if LOD == '1.1':
                face1 = "%s %s %s %s %s" % (p[1], p[2], p[6], p[5], p[1])
                faces.append(face1)
                faceBottom = "%s %s %s %s %s" % (p[0], p[3], p[2], p[1], p[0])
                faces.append(faceBottom)
                faceTop = "%s %s %s %s %s" % (p[4], p[5], p[6], p[7], p[4])
                faces.append(faceTop)
            elif LOD == '1.2':
                faceBottom = "%s %s %s %s %s %s %s %s %s" % (p[0], p[3], p[2], bp[3], bp[2], bp[1], bp[0], p[1], p[0])
                faces.append(faceBottom)
                faceTop = "%s %s %s %s %s %s %s %s %s" % (p[4], p[5], bpT[4], bpT[5], bpT[6], bpT[7], p[6], p[7], p[4])
                faces.append(faceTop)
                face1_0 = "%s %s %s %s %s" % (p[1], bp[0], bpT[4], p[5], p[1])
                faces.append(face1_0)
                face1_1 = "%s %s %s %s %s" % (p[2], p[6], bpT[7], bp[3], p[2])
                faces.append(face1_1)
                gface0 = "%s %s %s %s %s" % (bp[0], bp[1], bpT[5], bpT[4], bp[0])
                faces.append(gface0)
                gface1 = "%s %s %s %s %s" % (bp[1], bp[2], bpT[6], bpT[5], bp[1])
                faces.append(gface1)
                gface3 = "%s %s %s %s %s" % (bp[3], bpT[7], bpT[6], bp[2], bp[3])
                faces.append(gface3)
            elif LOD == '1.3':
                faceBottom = "%s %s %s %s %s %s %s %s %s" % (p[0], p[3], p[2], bp[3], bp[2], bp[1], bp[0], p[1], p[0])
                faces.append(faceBottom)
                faceTop = "%s %s %s %s %s" % (p[4], p[5], p[6], p[7], p[4])
                faces.append(faceTop)
                face1 = "%s %s %s %s %s %s %s %s %s" % (p[1], bp[0], bp[4], bp[7], bp[3], p[2], p[6], p[5], p[1])
                faces.append(face1)
                gface0 = "%s %s %s %s %s" % (bp[0], bp[1], bp[5], bp[4], bp[0])
                faces.append(gface0)
                gface1 = "%s %s %s %s %s" % (bp[1], bp[2], bp[6], bp[5], bp[1])
                faces.append(gface1)
                gface3 = "%s %s %s %s %s" % (bp[3], bp[7], bp[6], bp[2], bp[3])
                faces.append(gface3)
                gtop = "%s %s %s %s %s" % (bp[4], bp[5], bp[6], bp[7], bp[4])
                faces.append(gtop)                
        elif buildingpart['type'] == 'Garage':
            if LOD == '1.1' or LOD == '1.2' or LOD == '1.3':
                faceBottom = "%s %s %s %s %s %s %s %s %s" % (p[0], p[3], p[2], bp[3], bp[2], bp[1], bp[0], p[1], p[0])
                faces.append(faceBottom)
                if LOD == '1.1' or LOD == '1.2':
                    faceTop = "%s %s %s %s %s %s %s %s %s" % (p[4], p[5], bpT[4], bpT[5], bpT[6], bpT[7], p[6], p[7], p[4])
                    faces.append(faceTop)
                    face1_0 = "%s %s %s %s %s" % (p[1], bp[0], bpT[4], p[5], p[1])
                    faces.append(face1_0)
                    face1_1 = "%s %s %s %s %s" % (p[2], p[6], bpT[7], bp[3], p[2])
                    faces.append(face1_1)
                    gface0 = "%s %s %s %s %s" % (bp[0], bp[1], bpT[5], bpT[4], bp[0])
                    faces.append(gface0)
                    gface1 = "%s %s %s %s %s" % (bp[1], bp[2], bpT[6], bpT[5], bp[1])
                    faces.append(gface1)
                    gface3 = "%s %s %s %s %s" % (bp[3], bpT[7], bpT[6], bp[2], bp[3])
                    faces.append(gface3)
                elif LOD == '1.3':
                    faceTop = "%s %s %s %s %s" % (p[4], p[5], p[6], p[7], p[4])
                    faces.append(faceTop)
                    face1 = "%s %s %s %s %s %s %s %s %s" % (p[1], bp[0], bp[4], bp[7], bp[3], p[2], p[6], p[5], p[1])
                    faces.append(face1)
                    gface0 = "%s %s %s %s %s" % (bp[0], bp[1], bp[5], bp[4], bp[0])
                    faces.append(gface0)
                    gface1 = "%s %s %s %s %s" % (bp[1], bp[2], bp[6], bp[5], bp[1])
                    faces.append(gface1)
                    gface3 = "%s %s %s %s %s" % (bp[3], bp[7], bp[6], bp[2], bp[3])
                    faces.append(gface3)
                    gtop = "%s %s %s %s %s" % (bp[4], bp[5], bp[6], bp[7], bp[4])
                    faces.append(gtop)
    else:
        face1 = "%s %s %s %s %s" % (p[1], p[2], p[6], p[5], p[1])
        faces.append(face1)
        faceBottom = "%s %s %s %s %s" % (p[0], p[3], p[2], p[1], p[0])
        faces.append(faceBottom)
        faceTop = "%s %s %s %s %s" % (p[4], p[5], p[6], p[7], p[4])
        faces.append(faceTop)

    for face in faces:
        addsurface(False, CompositeSurface, face)


def CityGMLbuildingLOD2Solid(CityModel, ID, attributes, o, x, y, z, h, rtype=None, width=None, ovh=None, rep=None, LOD=None, aux=None, buildingpart=None, fd=False):
    """
    Create LOD2 of the building with a basic roof shape. Solid representation.
    """
    cityObject = etree.SubElement(CityModel, "cityObjectMember")
    bldg = etree.SubElement(cityObject, "{%s}Building" % ns_bldg)
    bldg.attrib['{%s}id' % ns_gml] = ID
    roofType = etree.SubElement(bldg, "{%s}roofType" % ns_bldg)
    roofType.text = rtype
    
    yearOfConstructionXML = etree.SubElement(bldg, "{%s}yearOfConstruction" % ns_bldg)
    yearOfConstructionXML.text = attributes['yearOfConstruction']
    functionXML = etree.SubElement(bldg, "{%s}function" % ns_bldg)
    functionXML.text = attributes['function']
    storeysAboveGroundXML = etree.SubElement(bldg, "{%s}storeysAboveGround" % ns_bldg)
    storeysAboveGroundXML.text = attributes['storeysAboveGround']

    p = verticesBody(o, x, y, z)
    r = verticesRoof([o, x, y, z], h, rtype, width)

    #-- Computations for the LOD2 with explicit overhangs
    eaves = z
    upperEaves = z
    if ovh is not None:
        overhangs, interiors, eaves, ovhy_recalculated = verticesOverhangs([o, x, y, z], p, h, rtype, ovh, r, width)
        if rtype == 'Shed':
            upperEaves = z + h + (z - eaves)
    else:
        overhangs = None

    if rep == 'solid':
        lod2rep = etree.SubElement(bldg, "{%s}lod2Solid" % ns_bldg)
        repres = etree.SubElement(lod2rep, "{%s}Solid" % ns_gml)
        exterior = etree.SubElement(repres, "{%s}exterior" % ns_gml)
        CompositeSurface = etree.SubElement(exterior, "{%s}CompositeSurface" % ns_gml)
    elif rep == 'brep':
        lod2rep = etree.SubElement(bldg, "{%s}lod2MultiSurface" % ns_bldg)
        repres = etree.SubElement(lod2rep, "{%s}MultiSurface" % ns_gml)
        surfaceMember = etree.SubElement(repres, "{%s}surfaceMember" % ns_gml)
    if ASSIGNID:
        repres.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
    

    #-- Is the building part covered by overhangs?
    if buildingpart is not None:
        if x > aux['xsize'] and aux['ovhx'] >= buildingpart['x']:
            covered = True
        else:
            covered = False
    else:
        covered = None

    east_faces = {}
    east_faces['rest'] = []
    east_faces['roof'] = []
    east_faces['outerfloor'] = []
    #-- Account for building parts
    if buildingpart is not None and not covered:

        #-- Accounting for overhangs
        if x > aux['xsize']:# or x < aux['xsize']:
            bp = [None] * 8
            bp[0] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[1] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[2] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[3] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[4] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])
            bp[7] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])

            #-- Top with the rest of the building
            bpT = [None] * 8
            tH = GMLstring2points(p[4])[0][2]
            bpT[4] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'], tH])
            bpT[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], tH])
            bpT[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])
            bpT[7] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])

        elif fd and x < aux['xsize']:

            bp = [None] * 8
            eastline = GMLstring2points(p[1])[0][0]
            bp[0] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[1] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[2] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[3] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[4] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])
            bp[7] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])

            #-- Top with the rest of the building
            bpT = [None] * 8
            tH = GMLstring2points(p[4])[0][2]
            bpT[4] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'], tH])
            bpT[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], tH])
            bpT[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])
            bpT[7] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])


        else:
            bp = [None] * 8
            bp[0] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[1] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[2] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[3] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[4] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[5] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[6] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])
            bp[7] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])

            #-- Top with the rest of the building
            bpT = [None] * 8
            tH = GMLstring2points(p[4])[0][2]
            bpT[4] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'], tH])
            bpT[5] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'], tH])
            bpT[6] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])
            bpT[7] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])

        if buildingpart['type'] == 'Alcove':
            if LOD == '2.0':
                face1 = "%s %s %s %s %s" % (p[1], p[2], p[6], p[5], p[1])
                east_faces['wall'] = face1
                faceBottom = "%s %s %s %s %s" % (p[0], p[3], p[2], p[1], p[0])

            elif LOD == '2.1' or LOD == '2.2' or LOD == '2.3':
                faceBottom = "%s %s %s %s %s %s %s %s %s" % (p[0], p[3], p[2], bp[3], bp[2], bp[1], bp[0], p[1], p[0])

                face1 = "%s %s %s %s %s %s %s %s %s" % (p[1], bp[0], bp[4], bp[7], bp[3], p[2], p[6], p[5], p[1])
                east_faces['wall'] = face1
                gface0 = "%s %s %s %s %s" % (bp[0], bp[1], bp[5], bp[4], bp[0])
                east_faces['rest'].append(gface0)
                gface1 = "%s %s %s %s %s" % (bp[1], bp[2], bp[6], bp[5], bp[1])
                east_faces['rest'].append(gface1)
                gface3 = "%s %s %s %s %s" % (bp[3], bp[7], bp[6], bp[2], bp[3])
                east_faces['rest'].append(gface3)
                gtop = "%s %s %s %s %s" % (bp[4], bp[5], bp[6], bp[7], bp[4])
                east_faces['outerfloor'].append(gtop)                
        elif buildingpart['type'] == 'Garage':
            if LOD == '2.0' or LOD == '2.1' or LOD == '2.2' or LOD == '2.3':
                faceBottom = "%s %s %s %s %s %s %s %s %s" % (p[0], p[3], p[2], bp[3], bp[2], bp[1], bp[0], p[1], p[0])
                face1 = "%s %s %s %s %s %s %s %s %s" % (p[1], bp[0], bp[4], bp[7], bp[3], p[2], p[6], p[5], p[1])
                east_faces['wall'] = face1
                gface0 = "%s %s %s %s %s" % (bp[0], bp[1], bp[5], bp[4], bp[0])
                east_faces['rest'].append(gface0)
                gface1 = "%s %s %s %s %s" % (bp[1], bp[2], bp[6], bp[5], bp[1])
                east_faces['rest'].append(gface1)
                gface3 = "%s %s %s %s %s" % (bp[3], bp[7], bp[6], bp[2], bp[3])
                east_faces['rest'].append(gface3)
                gtop = "%s %s %s %s %s" % (bp[4], bp[5], bp[6], bp[7], bp[4])
                east_faces['roof'].append(gtop)
    else:
        face1 = "%s %s %s %s %s" % (p[1], p[2], p[6], p[5], p[1])
        east_faces['wall'] = face1
        faceBottom = "%s %s %s %s %s" % (p[0], p[3], p[2], p[1], p[0])

    #-- Bottom face (in all cases regardless of the roof type)
    faceBottom = "%s %s %s %s %s" % (p[0], p[3], p[2], p[1], p[0])
    if rep == 'solid':
        addsurface(False, CompositeSurface, faceBottom)
    elif rep == 'brep':
        plainMultiSurface(surfaceMember, faceBottom)

    #-- Roof surfaces and wall surfaces depending on the type of the roof.
    if rtype == 'Gabled':
        if rep == 'solid':
            gabledRoof(CompositeSurface, p, r, east_faces)
        elif rep == 'brep':
            gabledRoof(surfaceMember, p, r, east_faces)
            if overhangs is not None and ovh[0] > 0:
                roofOverhangs(surfaceMember, overhangs, interiors)

    elif rtype == 'Shed':
        if rep == 'solid':
            shedRoof(CompositeSurface, p, r, east_faces)
        elif rep == 'brep':
            shedRoof(surfaceMember, p, r, east_faces)
            if overhangs is not None and ovh[0] > 0:
                roofOverhangs(surfaceMember, overhangs, interiors)
        #shedRoof(CompositeSurface, p, r, east_faces)

    elif rtype == 'Hipped' or rtype == 'Pyramidal':
        if rep == 'solid':
            hippedRoof(CompositeSurface, p, r, east_faces)
        elif rep == 'brep':
            hippedRoof(surfaceMember, p, r, east_faces)
            if overhangs is not None and ovh[0] > 0:
                roofOverhangs(surfaceMember, overhangs, interiors)
        #hippedRoof(CompositeSurface, p, r, east_faces)

    elif rtype == 'Flat' or None:
        if rep == 'solid':
            flatRoof(CompositeSurface, p, r, east_faces)
        elif rep == 'brep':
            flatRoof(surfaceMember, p, r, east_faces)
            if overhangs is not None and ovh[0] > 0:
                roofOverhangs(surfaceMember, overhangs, interiors)
        #flatRoof(CompositeSurface, p, r, east_faces)

def CityGMLbuildingLOD2Semantics(CityModel, ID, attributes, o, x, y, z, h, rtype=None, width=None, ovh=None, LOD=None, aux=None, buildingpart=None, fd=False):
    """
    Create LOD2 of the building with a basic roof shape and standard semantics (brep multisurfaces).
    """
    cityObject = etree.SubElement(CityModel, "cityObjectMember")
    bldg = etree.SubElement(cityObject, "{%s}Building" % ns_bldg)
    bldg.attrib['{%s}id' % ns_gml] = ID
    roofType = etree.SubElement(bldg, "{%s}roofType" % ns_bldg)
    roofType.text = rtype

    yearOfConstructionXML = etree.SubElement(bldg, "{%s}yearOfConstruction" % ns_bldg)
    yearOfConstructionXML.text = attributes['yearOfConstruction']
    functionXML = etree.SubElement(bldg, "{%s}function" % ns_bldg)
    functionXML.text = attributes['function']
    storeysAboveGroundXML = etree.SubElement(bldg, "{%s}storeysAboveGround" % ns_bldg)
    storeysAboveGroundXML.text = attributes['storeysAboveGround']

    p = verticesBody(o, x, y, z)
    r = verticesRoof([o, x, y, z], h, rtype, width)

    #-- Computations for the LOD2 with explicit overhangs
    eaves = z
    upperEaves = z
    if ovh is not None:
        overhangs, interiors, eaves, ovhy_recalculated = verticesOverhangs([o, x, y, z], p, h, rtype, ovh, r, width)
        if rtype == 'Shed':
            upperEaves = z + h + (z - eaves)
    else:
        overhangs = None

    #-- Is the building part covered by overhangs?
    if buildingpart is not None:
        if x > aux['xsize'] and aux['ovhx'] >= buildingpart['x']:
            covered = True
        else:
            covered = False
    else:
        covered = None

    east_faces = {}
    east_faces['rest'] = []
    east_faces['roof'] = []
    east_faces['outerfloor'] = []
    #-- Account for building parts
    if buildingpart is not None and not covered:

        #-- Accounting for overhangs
        if x > aux['xsize']:# or x < aux['xsize']:
            bp = [None] * 8
            bp[0] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[1] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[2] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[3] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[4] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])
            bp[7] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])

            #-- Top with the rest of the building
            bpT = [None] * 8
            tH = GMLstring2points(p[4])[0][2]
            bpT[4] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'], tH])
            bpT[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], tH])
            bpT[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])
            bpT[7] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])

        elif fd and x < aux['xsize']:

            bp = [None] * 8
            eastline = GMLstring2points(p[1])[0][0]
            bp[0] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[1] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[2] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[3] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[4] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])
            bp[7] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])

            #-- Top with the rest of the building
            bpT = [None] * 8
            tH = GMLstring2points(p[4])[0][2]
            bpT[4] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'], tH])
            bpT[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], tH])
            bpT[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])
            bpT[7] = GMLPointList([eastline, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])


        else:
            bp = [None] * 8
            bp[0] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[1] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
            bp[2] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[3] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
            bp[4] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[5] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
            bp[6] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])
            bp[7] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])

            #-- Top with the rest of the building
            bpT = [None] * 8
            tH = GMLstring2points(p[4])[0][2]
            bpT[4] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'], tH])
            bpT[5] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'], tH])
            bpT[6] = GMLPointList([aux['origin'][0] + aux['xsize'] + buildingpart['x'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])
            bpT[7] = GMLPointList([aux['origin'][0] + aux['xsize'], aux['origin'][1] + buildingpart['o'] + buildingpart['y'], tH])

        if buildingpart['type'] == 'Alcove':
            if LOD == '2.0':
                face1 = "%s %s %s %s %s" % (p[1], p[2], p[6], p[5], p[1])
                east_faces['wall'] = face1
                faceBottom = "%s %s %s %s %s" % (p[0], p[3], p[2], p[1], p[0])

            elif LOD == '2.1' or LOD == '2.2' or LOD == '2.3':
                faceBottom = "%s %s %s %s %s %s %s %s %s" % (p[0], p[3], p[2], bp[3], bp[2], bp[1], bp[0], p[1], p[0])
                face1 = "%s %s %s %s %s %s %s %s %s" % (p[1], bp[0], bp[4], bp[7], bp[3], p[2], p[6], p[5], p[1])
                east_faces['wall'] = face1
                gface0 = "%s %s %s %s %s" % (bp[0], bp[1], bp[5], bp[4], bp[0])
                east_faces['rest'].append(gface0)
                gface1 = "%s %s %s %s %s" % (bp[1], bp[2], bp[6], bp[5], bp[1])
                east_faces['rest'].append(gface1)
                gface3 = "%s %s %s %s %s" % (bp[3], bp[7], bp[6], bp[2], bp[3])
                east_faces['rest'].append(gface3)
                gtop = "%s %s %s %s %s" % (bp[4], bp[5], bp[6], bp[7], bp[4])
                east_faces['outerfloor'].append(gtop)                
        elif buildingpart['type'] == 'Garage':
            if LOD == '2.0' or LOD == '2.1' or LOD == '2.2' or LOD == '2.3':
                faceBottom = "%s %s %s %s %s %s %s %s %s" % (p[0], p[3], p[2], bp[3], bp[2], bp[1], bp[0], p[1], p[0])
                face1 = "%s %s %s %s %s %s %s %s %s" % (p[1], bp[0], bp[4], bp[7], bp[3], p[2], p[6], p[5], p[1])
                east_faces['wall'] = face1
                gface0 = "%s %s %s %s %s" % (bp[0], bp[1], bp[5], bp[4], bp[0])
                east_faces['rest'].append(gface0)
                gface1 = "%s %s %s %s %s" % (bp[1], bp[2], bp[6], bp[5], bp[1])
                east_faces['rest'].append(gface1)
                gface3 = "%s %s %s %s %s" % (bp[3], bp[7], bp[6], bp[2], bp[3])
                east_faces['rest'].append(gface3)
                gtop = "%s %s %s %s %s" % (bp[4], bp[5], bp[6], bp[7], bp[4])
                east_faces['roof'].append(gtop)
    else:
        face1 = "%s %s %s %s %s" % (p[1], p[2], p[6], p[5], p[1])
        east_faces['wall'] = face1
        faceBottom = "%s %s %s %s %s" % (p[0], p[3], p[2], p[1], p[0])

    #-- Bottom face (in all cases regardless of the roof type)
    multiSurface(bldg, faceBottom, "GroundSurface", None)

    #-- Roof surfaces and wall surfaces depending on the type of the roof.
    if rtype == 'Gabled':
        gabledRoof(bldg, p, r, east_faces, True)
        if overhangs is not None and ovh[0] > 0:
            roofOverhangs(bldg, overhangs, interiors, True)

    elif rtype == 'Shed':
        shedRoof(bldg, p, r, east_faces, True)
        if overhangs is not None and ovh[0] > 0:
            roofOverhangs(bldg, overhangs, interiors, True)

    elif rtype == 'Hipped' or rtype == 'Pyramidal':
        hippedRoof(bldg, p, r, east_faces, True)
        if overhangs is not None and ovh[0] > 0:
            roofOverhangs(bldg, overhangs, interiors, True)

    elif rtype == 'Flat' or None:
        flatRoof(bldg, p, r, east_faces, True)
        if overhangs is not None and ovh[0] > 0:
            roofOverhangs(bldg, overhangs, interiors, True)

def CityGMLbuildingLOD3Semantics(CityModel, ID, attributes, o, x, y, z, h, rtype=None, ovh=None, width=None, door=None, wallWindows=None, dormers=None, roofWindows=None, chimney=None, embrasure=None, BiSem=1, aux=None, buildingpart=None, aerial=False):
    """
    Create LOD3 of the building with an advanced roof shape and semantics (multisurfaces).
    """
    cityObject = etree.SubElement(CityModel, "cityObjectMember")
    bldg = etree.SubElement(cityObject, "{%s}Building" % ns_bldg)
    bldg.attrib['{%s}id' % ns_gml] = ID
    roofType = etree.SubElement(bldg, "{%s}roofType" % ns_bldg)
    roofType.text = rtype

    yearOfConstructionXML = etree.SubElement(bldg, "{%s}yearOfConstruction" % ns_bldg)
    yearOfConstructionXML.text = attributes['yearOfConstruction']
    functionXML = etree.SubElement(bldg, "{%s}function" % ns_bldg)
    functionXML.text = attributes['function']
    storeysAboveGroundXML = etree.SubElement(bldg, "{%s}storeysAboveGround" % ns_bldg)
    storeysAboveGroundXML.text = attributes['storeysAboveGround']

    p = verticesBody(o, x, y, z)
    pList = verticesBodyList(o, x, y, z)
    r = verticesRoof([o, x, y, z], h, rtype, width)
    if r == []:
        r = None

    eaves = z
    upperEaves = z
    if ovh is not None:
        overhangs, interiors, eaves, ovhy_recalculated = verticesOverhangs([o, x, y, z], p, h, rtype, ovh, r, width)
        if rtype == 'Shed':
            upperEaves = z + h + (z - eaves)
    else:
        ovhy_recalculated = None

    #-- Is the building part covered by overhangs?
    if buildingpart is not None and aerial is True:
        if x > aux['xsize'] and aux['ovhx'] >= buildingpart['x']:
            covered = True
        else:
            covered = False
    else:
        covered = None

    east_faces = {}
    east_faces['rest'] = []
    east_faces['roof'] = []
    east_faces['outerfloor'] = []
    #-- Account for building parts
    if buildingpart is not None and not covered:

        bp = [None] * 8
        bp[0] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
        bp[1] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
        bp[2] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
        bp[3] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
        bp[4] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
        bp[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
        bp[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])
        bp[7] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])

        faceBottom = "%s %s %s %s %s %s %s %s %s" % (p[0], p[3], p[2], bp[3], bp[2], bp[1], bp[0], p[1], p[0])
        face1 = "%s %s %s %s %s %s %s %s %s" % (p[1], bp[0], bp[4], bp[7], bp[3], p[2], p[6], p[5], p[1])
        east_faces['wall'] = face1
        gface0 = "%s %s %s %s %s" % (bp[0], bp[1], bp[5], bp[4], bp[0])
        east_faces['rest'].append(gface0)
        gface1 = "%s %s %s %s %s" % (bp[1], bp[2], bp[6], bp[5], bp[1])
        east_faces['rest'].append(gface1)
        gface3 = "%s %s %s %s %s" % (bp[3], bp[7], bp[6], bp[2], bp[3])
        east_faces['rest'].append(gface3)
        gtop = "%s %s %s %s %s" % (bp[4], bp[5], bp[6], bp[7], bp[4])
        if buildingpart['type'] == 'Alcove':
            east_faces['outerfloor'].append(gtop)
        elif buildingpart['type'] == 'Garage':
            east_faces['roof'].append(gtop)
    else:
        face1 = "%s %s %s %s %s" % (p[1], p[2], p[6], p[5], p[1])
        east_faces['wall'] = face1
        faceBottom = "%s %s %s %s %s" % (p[0], p[3], p[2], p[1], p[0])

    ropenings = [[], [], [], []]
    ropenings_rw = [[], [], [], []]

    #-- Dormers
    if dormers or roofWindows:
        if dormers and len(dormers) > 0:
            for drm in dormers:
                #-- Get a list of vertices of each dormer
                dList, dListGML = dormerVertices([drm], pList, h, rtype, [o, x, y, z], width)
                #-- Get the opening for creating a hole in the roof surface
                #--Inverted
                ropenings[int(drm['side'])].append(str(dListGML[0][0] + ' ' + dListGML[0][3] + ' ' + dListGML[0][2] + ' ' + dListGML[0][1] + ' ' + dListGML[0][0]))
                #-- Construct the dormer
                if aerial is True:
                    buildinginstallation(bldg, "dormer", [dList[0], dListGML[0]], BiSem, None, drm['side'], embrasure)
                elif aerial is None or aerial is False:
                    buildinginstallation(bldg, "dormer", [dList[0], dListGML[0]], BiSem, 0.1, drm['side'], embrasure)
        elif roofWindows and len(roofWindows) > 0:
            # ropenings_rw.append("")
            # ropenings_rw.append([])
            for rfw in roofWindows:
                #-- Get a list of vertices of each window. It is the same as for dormer so the same function is used.
                dList, dListGML = dormerVertices([rfw], pList, h, rtype, [o, x, y, z], width)
                #-- Get the opening for creating a hole in the roof surface
                ropenings[int(rfw['side'])].append(str(dListGML[0][0] + ' ' + dListGML[0][3] + ' ' + dListGML[0][2] + ' ' + dListGML[0][1] + ' ' + dListGML[0][0])) 
                ropenings_rw[int(rfw['side'])].append(str(dListGML[0][0] + ' ' + dListGML[0][1] + ' ' + dListGML[0][2] + ' ' + dListGML[0][3] + ' ' + dListGML[0][0])) 

    #-- Deal with chimney(s)
    if chimney:
        if len(chimney) > 0:
            for ch in chimney:
                #-- List of vertices
                dList, dListGML = chimneyVertices([ch], pList, h, rtype, [o, x, y, z], width)
                #-- Get the opening for creating a hole in the roof surface
                ropenings[int(ch['side'])].append(str(dListGML[0][0] + ' ' + dListGML[0][3] + ' ' + dListGML[0][2] + ' ' + dListGML[0][1] + ' ' + dListGML[0][0]))
                #-- Construct the chimney
                buildinginstallation(bldg, "chimney", [dList[0], dListGML[0]], BiSem, None, ch['side'])
                chimneyHeight = dList[0][7][2]
    else:
        chimneyHeight = None


    #-- Bottom face (in all cases the same regardless of the roof type)
    #faceBottom = "%s %s %s %s %s" % (p[0], p[3], p[2], p[1], p[0])
    multiSurface(bldg, faceBottom, "GroundSurface", None, 3)

    openings = []
    #-- Door
    if door:
        door['ring'] = openingRing(door, pList)
        openings.append(door)
    else:
        openings.append("")

    if wallWindows:
        if len(wallWindows) > 0:
            openings.append([])
            i = 0
            for ww in wallWindows:
                wallWindows[i]['ring'] = openingRing(ww, pList)
                openings[1].append(wallWindows[i])
                i += 1
    else:
        openings.append("")



    #-- Roof surfaces and wall surfaces depending on the type of the roof.
    if rtype == 'Gabled':
        gabledRoof(bldg, p, r, east_faces, True, openings, ropenings, ropenings_rw, embrasure, pList)
        if ovh[0] > 0:
            roofOverhangs(bldg, overhangs, interiors, True)

    elif rtype == 'Shed':
        shedRoof(bldg, p, r, east_faces, True, openings, ropenings, ropenings_rw, embrasure, pList)
        if ovh[0] > 0:
            roofOverhangs(bldg, overhangs, interiors, True)

    elif rtype == 'Hipped' or rtype == 'Pyramidal':
        hippedRoof(bldg, p, r, east_faces, True, openings, ropenings, ropenings_rw, embrasure, pList)
        if ovh[0] > 0:
            roofOverhangs(bldg, overhangs, interiors, True)

    elif rtype == 'Flat' or None:
        flatRoof(bldg, p, r, east_faces, True, openings, ropenings, ropenings_rw, embrasure, pList)
        if ovh[0] > 0:
            roofOverhangs(bldg, overhangs, interiors, True)


    if rtype == 'Shed':
        if chimneyHeight is not None:
            if chimneyHeight < upperEaves:
                chimneyHeight = upperEaves
        else:
            chimneyHeight = upperEaves

    return chimneyHeight, eaves, ovhy_recalculated


def CityGMLbuildingLOD3Solid(CityModel, ID, attributes, o, x, y, z, h, rtype=None, ovh=None, width=None, door=None, wallWindows=None, dormers=None, roofWindows=None, chimney=None, embrasure=None, additional=None, rep=None, aux=None, buildingpart=None, aerial=False):
    """
    Create LOD3 solid or plain geometry (brep without semantics).
    """
    cityObject = etree.SubElement(CityModel, "cityObjectMember")
    bldg = etree.SubElement(cityObject, "{%s}Building" % ns_bldg)
    bldg.attrib['{%s}id' % ns_gml] = ID
    roofType = etree.SubElement(bldg, "{%s}roofType" % ns_bldg)
    roofType.text = rtype

    yearOfConstructionXML = etree.SubElement(bldg, "{%s}yearOfConstruction" % ns_bldg)
    yearOfConstructionXML.text = attributes['yearOfConstruction']
    functionXML = etree.SubElement(bldg, "{%s}function" % ns_bldg)
    functionXML.text = attributes['function']
    storeysAboveGroundXML = etree.SubElement(bldg, "{%s}storeysAboveGround" % ns_bldg)
    storeysAboveGroundXML.text = attributes['storeysAboveGround']

    if rep == 'solid':
        lod3rep = etree.SubElement(bldg, "{%s}lod3Solid" % ns_bldg)
        repres = etree.SubElement(lod3rep, "{%s}Solid" % ns_gml)
        exterior = etree.SubElement(repres, "{%s}exterior" % ns_gml)
        CompositeSurface = etree.SubElement(exterior, "{%s}CompositeSurface" % ns_gml)
    elif rep == 'brep':
        lod3rep = etree.SubElement(bldg, "{%s}lod3MultiSurface" % ns_bldg)
        repres = etree.SubElement(lod3rep, "{%s}MultiSurface" % ns_gml)
        surfaceMember = etree.SubElement(repres, "{%s}surfaceMember" % ns_gml)
    if ASSIGNID:
        repres.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
    
    p = verticesBody(o, x, y, z)
    pList = verticesBodyList(o, x, y, z)
    r = verticesRoof([o, x, y, z], h, rtype, width)
    if r == []:
        r = None
    if ovh is not None:
        overhangs, interiors, eaves, ovhy_recalculated = verticesOverhangs([o, x, y, z], p, h, rtype, ovh, r, width)


    ropenings = [[], [], [], []]
    ropenings_rw = [[], [], [], []]

    #-- Is the building part covered by overhangs?
    if buildingpart is not None and aerial is True:
        if x > aux['xsize'] and aux['ovhx'] >= buildingpart['x']:
            covered = True
        else:
            covered = False
    else:
        covered = None

    east_faces = {}
    east_faces['rest'] = []
    east_faces['roof'] = []
    east_faces['outerfloor'] = []
    #-- Account for building parts
    if buildingpart is not None and not covered:

        bp = [None] * 8
        bp[0] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
        bp[1] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], aux['origin'][2]])
        bp[2] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
        bp[3] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2]])
        bp[4] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
        bp[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'], aux['origin'][2] + buildingpart['z']])
        bp[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']), aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])
        bp[7] = GMLPointList([o[0] + x, aux['origin'][1] + buildingpart['o'] + buildingpart['y'], aux['origin'][2] + buildingpart['z']])

        faceBottom = "%s %s %s %s %s %s %s %s %s" % (p[0], p[3], p[2], bp[3], bp[2], bp[1], bp[0], p[1], p[0])
        face1 = "%s %s %s %s %s %s %s %s %s" % (p[1], bp[0], bp[4], bp[7], bp[3], p[2], p[6], p[5], p[1])
        east_faces['wall'] = face1
        gface0 = "%s %s %s %s %s" % (bp[0], bp[1], bp[5], bp[4], bp[0])
        east_faces['rest'].append(gface0)
        gface1 = "%s %s %s %s %s" % (bp[1], bp[2], bp[6], bp[5], bp[1])
        east_faces['rest'].append(gface1)
        gface3 = "%s %s %s %s %s" % (bp[3], bp[7], bp[6], bp[2], bp[3])
        east_faces['rest'].append(gface3)
        gtop = "%s %s %s %s %s" % (bp[4], bp[5], bp[6], bp[7], bp[4])
        east_faces['roof'].append(gtop)
    else:
        face1 = "%s %s %s %s %s" % (p[1], p[2], p[6], p[5], p[1])
        east_faces['wall'] = face1
        faceBottom = "%s %s %s %s %s" % (p[0], p[3], p[2], p[1], p[0])

    #-- Dormers
    roofWindows = None
    if dormers or roofWindows:
        if dormers and len(dormers) > 0:
            for drm in dormers:
                #-- Get a list of vertices of each dormer
                dList, dListGML = dormerVertices([drm], pList, h, rtype, [o, x, y, z], width)
                #-- Get the opening for creating a hole in the roof surface
                ropenings[int(drm['side'])].append(str(dListGML[0][0] + ' ' + dListGML[0][3] + ' ' + dListGML[0][2] + ' ' + dListGML[0][1] + ' ' + dListGML[0][0]))
                #-- Construct the dormer
                if rep == 'solid':
                    if aerial is True:
                        buildinginstallationSolid(False, CompositeSurface, "dormer", [dList[0], dListGML[0]], 0, None, drm['side'], embrasure)    
                    else:
                        buildinginstallationSolid(False, CompositeSurface, "dormer", [dList[0], dListGML[0]], 0, 0.1, drm['side'], embrasure)
                elif rep == 'brep':
                    if aerial is True:
                        buildinginstallationSolid(False, surfaceMember, "dormer", [dList[0], dListGML[0]], 0, None, drm['side'], embrasure)
                    else:
                        buildinginstallationSolid(False, surfaceMember, "dormer", [dList[0], dListGML[0]], 0, 0.1, drm['side'], embrasure)

    #-- Bottom face (in all cases the same regardless of the roof type)
    #faceBottom = "%s %s %s %s %s" % (p[0], p[3], p[2], p[1], p[0])
    if rep == 'solid':
        addsurface(False, CompositeSurface, faceBottom)
    elif rep == 'brep':
        plainMultiSurface(surfaceMember, faceBottom)

    openings = []
    #-- Door
    if door:
        door['ring'] = openingRing(door, pList)
        openings.append(door)
    else:
        openings.append("")

    if wallWindows:
        if len(wallWindows) > 0:
            openings.append([])
            i = 0
            for ww in wallWindows:
                wallWindows[i]['ring'] = openingRing(ww, pList)
                openings[1].append(wallWindows[i])
                i += 1
    else:
        openings.append("")

    #-- Roof surfaces and wall surfaces depending on the type of the roof.
    if rtype == 'Gabled':
        if rep == 'solid':
            gabledRoof(CompositeSurface, p, r, east_faces, None, openings, ropenings, None, embrasure, pList)
        elif rep == 'brep':
            gabledRoof(surfaceMember, p, r, east_faces, None, openings, ropenings, None, embrasure, pList)
            if overhangs is not None and ovh[0] > 0:
                roofOverhangs(surfaceMember, overhangs, interiors)

    elif rtype == 'Shed':
        if rep == 'solid':
            shedRoof(CompositeSurface, p, r, east_faces, None, openings, ropenings, None, embrasure, pList)
        elif rep == 'brep':
            shedRoof(surfaceMember, p, r, east_faces, None, openings, ropenings, None, embrasure, pList)
            if overhangs is not None and ovh[0] > 0:
                roofOverhangs(surfaceMember, overhangs, interiors)

    elif rtype == 'Hipped' or rtype == 'Pyramidal':
        if rep == 'solid':
            hippedRoof(CompositeSurface, p, r, east_faces, None, openings, ropenings, None, embrasure, pList)
        elif rep == 'brep':
            hippedRoof(surfaceMember, p, r, east_faces, None, openings, ropenings, None, embrasure, pList)
            if overhangs is not None and ovh[0] > 0:
                roofOverhangs(surfaceMember, overhangs, interiors)

    elif rtype == 'Flat' or None:
        if rep == 'solid':
            flatRoof(CompositeSurface, p, r, east_faces, None, openings, ropenings, None, embrasure, pList)
        elif rep == 'brep':
            flatRoof(surfaceMember, p, r, east_faces, None, openings, ropenings, None, embrasure, pList)
            if overhangs is not None and ovh[0] > 0:
                roofOverhangs(surfaceMember, overhangs, interiors)


def CityGMLbuildingInteriorLOD0(CityModel, ID, attributes, o, x, y, z, h, floors, floorHeight, rtype=None, width=None, wallThickness=0.2, joist=0.2, aux=None, buildingpart=None):
    """Create the interior footprints. One for each storey."""
    cityObject = etree.SubElement(CityModel, "cityObjectMember")
    bldg = etree.SubElement(cityObject, "{%s}Building" % ns_bldg)
    bldg.attrib['{%s}id' % ns_gml] = ID
    roofType = etree.SubElement(bldg, "{%s}roofType" % ns_bldg)
    roofType.text = rtype

    yearOfConstructionXML = etree.SubElement(bldg, "{%s}yearOfConstruction" % ns_bldg)
    yearOfConstructionXML.text = attributes['yearOfConstruction']
    functionXML = etree.SubElement(bldg, "{%s}function" % ns_bldg)
    functionXML.text = attributes['function']
    storeysAboveGroundXML = etree.SubElement(bldg, "{%s}storeysAboveGround" % ns_bldg)
    storeysAboveGroundXML.text = attributes['storeysAboveGround']

    #-- Coordinates of the main interior points (offset from the exterior surface)
    Xa = o[0] + wallThickness
    Xb = o[0] + x - wallThickness
    Ya = o[1] + wallThickness
    Yb = o[1] + y - wallThickness

    if rtype != 'Flat':
        floors += 1

    #-- Construct a surface for each floor
    for floor in range(1, int(floors) + 1):
        #-- Floor elevation
        fel = (floor - 1) * floorHeight + 0.5*joist
        #-- Ceiling elevation
        cel = floor * floorHeight - 0.5*joist
        #-- XML tree
        lod1MultiSurface = etree.SubElement(bldg, "{%s}lod1MultiSurface" % ns_bldg)
        ms = etree.SubElement(lod1MultiSurface, "{%s}MultiSurface" % ns_gml)
        if ASSIGNID:
            ms.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
        # exterior = etree.SubElement(Solid, "{%s}exterior" % ns_gml)
        # CompositeSurface = etree.SubElement(exterior, "{%s}CompositeSurface" % ns_gml)
        #-- The eight points of the solid. F=Floor, C=Ceiling
        p0F = str(Xa) + ' ' + str(Ya) + ' ' + str(fel)
        p0C = str(Xa) + ' ' + str(Ya) + ' ' + str(cel)
        p1F = str(Xb) + ' ' + str(Ya) + ' ' + str(fel)
        p1C = str(Xb) + ' ' + str(Ya) + ' ' + str(cel)
        p2F = str(Xb) + ' ' + str(Yb) + ' ' + str(fel)
        p2C = str(Xb) + ' ' + str(Yb) + ' ' + str(cel)
        p3F = str(Xa) + ' ' + str(Yb) + ' ' + str(fel)
        p3C = str(Xa) + ' ' + str(Yb) + ' ' + str(cel)
        if floor == 1:
            if buildingpart is not None:
                if buildingpart['type'] == 'Alcove':
                    bp = [None] * 8
                    bp[0] = GMLPointList([o[0] + x - wallThickness, aux['origin'][1] + buildingpart['o'] + wallThickness, aux['origin'][2] + 0.5*joist])
                    bp[1] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']) - wallThickness, aux['origin'][1] + buildingpart['o'] + wallThickness, aux['origin'][2] + 0.5*joist])
                    bp[2] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']) - wallThickness, aux['origin'][1] + buildingpart['o'] + buildingpart['y'] - wallThickness, aux['origin'][2] + 0.5*joist])
                    bp[3] = GMLPointList([o[0] + x - wallThickness, aux['origin'][1] + buildingpart['o'] + buildingpart['y'] - wallThickness, aux['origin'][2] + 0.5*joist])
                    bp[4] = GMLPointList([o[0] + x - wallThickness, aux['origin'][1] + buildingpart['o'] + wallThickness, aux['origin'][2] + buildingpart['z'] - 0.5*joist])
                    bp[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']) - wallThickness, aux['origin'][1] + buildingpart['o'] + wallThickness, aux['origin'][2] + buildingpart['z'] - 0.5*joist])
                    bp[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']) - wallThickness, aux['origin'][1] + buildingpart['o'] + buildingpart['y'] - wallThickness, aux['origin'][2] + buildingpart['z'] - 0.5*joist])
                    bp[7] = GMLPointList([o[0] + x - wallThickness, aux['origin'][1] + buildingpart['o'] + buildingpart['y'] - wallThickness, aux['origin'][2] + buildingpart['z'] - 0.5*joist])
                    #E = "%s %s %s %s %s %s %s %s %s" % (p1F, bp[0], bp[4], bp[7], bp[3], p2F, p2C, p1C, p1F)
                    faceBottom = "%s %s %s %s %s %s %s %s %s" % (p0F, p3F, p2F, bp[3], bp[2], bp[1], bp[0], p1F, p0F)

                elif buildingpart['type'] == 'Garage':
                    #E = "%s %s %s %s %s" % (p1F, p2F, p2C, p1C, p1F)
                    faceBottom = "%s %s %s %s %s" % (p0F, p3F, p2F, p1F, p0F)
                    #top = "%s %s %s %s %s" % (p0C, p1C, p2C, p3C, p0C)
                    bp = [None] * 8
                    bp[0] = GMLPointList([o[0] + x + wallThickness, aux['origin'][1] + buildingpart['o'] + wallThickness, aux['origin'][2] + 0.5*joist])
                    bp[1] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']) - wallThickness, aux['origin'][1] + buildingpart['o'] + wallThickness, aux['origin'][2] + 0.5*joist])
                    bp[2] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']) - wallThickness, aux['origin'][1] + buildingpart['o'] + buildingpart['y'] - wallThickness, aux['origin'][2] + 0.5*joist])
                    bp[3] = GMLPointList([o[0] + x + wallThickness, aux['origin'][1] + buildingpart['o'] + buildingpart['y'] - wallThickness, aux['origin'][2] + 0.5*joist])
                    bp[4] = GMLPointList([o[0] + x + wallThickness, aux['origin'][1] + buildingpart['o'] + wallThickness, aux['origin'][2] + buildingpart['z'] - 0.5*joist])
                    bp[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']) - wallThickness, aux['origin'][1] + buildingpart['o'] + wallThickness, aux['origin'][2] + buildingpart['z'] - 0.5*joist])
                    bp[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']) - wallThickness, aux['origin'][1] + buildingpart['o'] + buildingpart['y'] - wallThickness, aux['origin'][2] + buildingpart['z'] - 0.5*joist])
                    bp[7] = GMLPointList([o[0] + x + wallThickness, aux['origin'][1] + buildingpart['o'] + buildingpart['y'] - wallThickness, aux['origin'][2] + buildingpart['z'] - 0.5*joist])
                    gbottom = "%s %s %s %s %s" % (bp[0], bp[3], bp[2], bp[1], bp[0])
                    addsurface(False, ms, gbottom)

            else:
                # E = "%s %s %s %s %s" % (p1F, p2F, p2C, p1C, p1F)
                faceBottom = "%s %s %s %s %s" % (p0F, p3F, p2F, p1F, p0F)
                # top = "%s %s %s %s %s" % (p0C, p1C, p2C, p3C, p0C)
        else:
            faceBottom = "%s %s %s %s %s" % (p0F, p3F, p2F, p1F, p0F)

        addsurface(False, ms, faceBottom)



def CityGMLbuildingInteriorLOD1(CityModel, ID, attributes, o, x, y, z, h, floors, floorHeight, rtype=None, width=None, wallThickness=0.2, joist=0.2, aux=None, buildingpart=None):
    """Create the interior of an "LOD1+" according to (Boeters et al., 2015)."""
    cityObject = etree.SubElement(CityModel, "cityObjectMember")
    bldg = etree.SubElement(cityObject, "{%s}Building" % ns_bldg)
    bldg.attrib['{%s}id' % ns_gml] = ID
    roofType = etree.SubElement(bldg, "{%s}roofType" % ns_bldg)
    roofType.text = rtype

    yearOfConstructionXML = etree.SubElement(bldg, "{%s}yearOfConstruction" % ns_bldg)
    yearOfConstructionXML.text = attributes['yearOfConstruction']
    functionXML = etree.SubElement(bldg, "{%s}function" % ns_bldg)
    functionXML.text = attributes['function']
    storeysAboveGroundXML = etree.SubElement(bldg, "{%s}storeysAboveGround" % ns_bldg)
    storeysAboveGroundXML.text = attributes['storeysAboveGround']

    #-- Coordinates of the main interior points (offset from the exterior surface)
    Xa = o[0] + wallThickness
    Xb = o[0] + x - wallThickness
    Ya = o[1] + wallThickness
    Yb = o[1] + y - wallThickness

    #-- Floor elevation
    fel = 0.5*joist
    #-- Ceiling elevation
    if rtype == 'Flat':
        cel = floors * floorHeight - 0.5*joist
    else:
        cel = floors * floorHeight + 0.5*joist
    #-- XML tree
    lod2Solid = etree.SubElement(bldg, "{%s}lod2Solid" % ns_bldg)
    Solid = etree.SubElement(lod2Solid, "{%s}Solid" % ns_gml)
    if ASSIGNID:
        Solid.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
    exterior = etree.SubElement(Solid, "{%s}exterior" % ns_gml)
    CompositeSurface = etree.SubElement(exterior, "{%s}CompositeSurface" % ns_gml)
    #-- The eight points of the solid. F=Floor, C=Ceiling
    p0F = str(Xa) + ' ' + str(Ya) + ' ' + str(fel)
    p0C = str(Xa) + ' ' + str(Ya) + ' ' + str(cel)
    p1F = str(Xb) + ' ' + str(Ya) + ' ' + str(fel)
    p1C = str(Xb) + ' ' + str(Ya) + ' ' + str(cel)
    p2F = str(Xb) + ' ' + str(Yb) + ' ' + str(fel)
    p2C = str(Xb) + ' ' + str(Yb) + ' ' + str(cel)
    p3F = str(Xa) + ' ' + str(Yb) + ' ' + str(fel)
    p3C = str(Xa) + ' ' + str(Yb) + ' ' + str(cel)
    
    S = "%s %s %s %s %s" % (p0F, p1F, p1C, p0C, p0F)
    if buildingpart is not None:
        bp = [None] * 8
        bp[0] = GMLPointList([o[0] + x - wallThickness, aux['origin'][1] + buildingpart['o'] + wallThickness, aux['origin'][2] + 0.5*joist])
        bp[1] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']) - wallThickness, aux['origin'][1] + buildingpart['o'] + wallThickness, aux['origin'][2] + 0.5*joist])
        bp[2] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']) - wallThickness, aux['origin'][1] + buildingpart['o'] + buildingpart['y'] - wallThickness, aux['origin'][2] + 0.5*joist])
        bp[3] = GMLPointList([o[0] + x - wallThickness, aux['origin'][1] + buildingpart['o'] + buildingpart['y'] - wallThickness, aux['origin'][2] + 0.5*joist])
        bp[4] = GMLPointList([o[0] + x - wallThickness, aux['origin'][1] + buildingpart['o'] + wallThickness, aux['origin'][2] + buildingpart['z'] - 0.5*joist])
        bp[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']) - wallThickness, aux['origin'][1] + buildingpart['o'] + wallThickness, aux['origin'][2] + buildingpart['z'] - 0.5*joist])
        bp[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']) - wallThickness, aux['origin'][1] + buildingpart['o'] + buildingpart['y'] - wallThickness, aux['origin'][2] + buildingpart['z'] - 0.5*joist])
        bp[7] = GMLPointList([o[0] + x - wallThickness, aux['origin'][1] + buildingpart['o'] + buildingpart['y'] - wallThickness, aux['origin'][2] + buildingpart['z'] - 0.5*joist])
        E = "%s %s %s %s %s %s %s %s %s" % (p1F, bp[0], bp[4], bp[7], bp[3], p2F, p2C, p1C, p1F)
        faceBottom = "%s %s %s %s %s %s %s %s %s" % (p0F, p3F, p2F, bp[3], bp[2], bp[1], bp[0], p1F, p0F)
        gface0 = "%s %s %s %s %s" % (bp[0], bp[1], bp[5], bp[4], bp[0])
        gface1 = "%s %s %s %s %s" % (bp[1], bp[2], bp[6], bp[5], bp[1])
        gface3 = "%s %s %s %s %s" % (bp[3], bp[7], bp[6], bp[2], bp[3])
        gtop = "%s %s %s %s %s" % (bp[4], bp[5], bp[6], bp[7], bp[4])
        addsurface(False, CompositeSurface, gface0)
        addsurface(False, CompositeSurface, gface1)
        addsurface(False, CompositeSurface, gface3)
        addsurface(False, CompositeSurface, gtop)
    else:
        E = "%s %s %s %s %s" % (p1F, p2F, p2C, p1C, p1F)
        faceBottom = "%s %s %s %s %s" % (p0F, p3F, p2F, p1F, p0F)
    N = "%s %s %s %s %s" % (p2F, p3F, p3C, p2C, p2F)
    W = "%s %s %s %s %s" % (p3F, p0F, p0C, p3C, p3F)
    addsurface(False, CompositeSurface, E)
    addsurface(False, CompositeSurface, faceBottom)
    addsurface(False, CompositeSurface, S)
    addsurface(False, CompositeSurface, N)
    addsurface(False, CompositeSurface, W)

    if rtype != 'Flat':
        p = verticesBody(o, x, y, z)
        pList = verticesBodyList(o, x, y, z)
        if rtype == 'Shed':
            h2 = (h/x) * (x - 2* wallThickness)
            topThickness = h - h2 - .5*joist
            rWth = (topThickness/h)*(x)
        else:
            h2 = (h/(.5*x)) * (.5*x - wallThickness)
            topThickness = h - h2 - .5*joist
            rWth = (topThickness/h)*(.5*x)

    #-- Extension for the attic
    if rtype != 'Flat':

        XTa = o[0] + wallThickness
        XTb = o[0] + x - wallThickness
        YTa = o[1] + wallThickness
        YTb = o[1] + y - wallThickness

        r = verticesRoof([o, x, y, z], h, rtype, width)
        r[0] = GMLstring2points(r[0])[0]
        r[1] = GMLstring2points(r[1])[0]
        #-- Floor elevation
        fel = floors * floorHeight + 0.5*joist
        #-- Ceiling elevation
        if rtype == 'Shed':
            h2 = (h/x) * (x - wallThickness)
            topThickness = h - h2 - .5*joist
        else:
            h2 = (h/(.5*x)) * (.5*x - wallThickness)
            topThickness = h - h2 - .5*joist
        cel = float(r[0][2]) - topThickness
        # #-- XML tree
        # lod2Solid = etree.SubElement(bldg, "{%s}lod2Solid" % ns_bldg)
        # Solid = etree.SubElement(lod2Solid, "{%s}Solid" % ns_gml)
        # if ASSIGNID:
        #     Solid.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
        # exterior = etree.SubElement(Solid, "{%s}exterior" % ns_gml)
        # CompositeSurface = etree.SubElement(exterior, "{%s}CompositeSurface" % ns_gml)
        if rtype == 'Gabled':
            gabledAttic(CompositeSurface, [XTa, YTa, XTb, YTb], p, r, fel, cel, wallThickness, topThickness)
        elif rtype == 'Hipped':
            hippedAttic(CompositeSurface, [XTa, YTa, XTb, YTb], p, r, fel, cel, wallThickness, topThickness)

        elif rtype == 'Pyramidal':
            pyramidalAttic(CompositeSurface, [XTa, YTa, XTb, YTb], p, r, fel, cel, wallThickness, topThickness)

        elif rtype == 'Shed':
            shedAttic(CompositeSurface, [XTa, YTa, XTb, YTb], p, r, fel, cel, wallThickness, topThickness)

    else:
        top = "%s %s %s %s %s" % (p0C, p1C, p2C, p3C, p0C)
        addsurface(False, CompositeSurface, top)


def CityGMLbuildingInteriorLOD2(CityModel, ID, attributes, o, x, y, z, h, floors, floorHeight, rtype=None, width=None, wallThickness=0.2, joist=0.2, aux=None, buildingpart=None, dormers=None):
    """Create the interior of an "LOD2+" according to (Boeters et al., 2015)."""
    cityObject = etree.SubElement(CityModel, "cityObjectMember")
    bldg = etree.SubElement(cityObject, "{%s}Building" % ns_bldg)
    bldg.attrib['{%s}id' % ns_gml] = ID
    roofType = etree.SubElement(bldg, "{%s}roofType" % ns_bldg)
    roofType.text = rtype

    yearOfConstructionXML = etree.SubElement(bldg, "{%s}yearOfConstruction" % ns_bldg)
    yearOfConstructionXML.text = attributes['yearOfConstruction']
    functionXML = etree.SubElement(bldg, "{%s}function" % ns_bldg)
    functionXML.text = attributes['function']
    storeysAboveGroundXML = etree.SubElement(bldg, "{%s}storeysAboveGround" % ns_bldg)
    storeysAboveGroundXML.text = attributes['storeysAboveGround']

    #-- Coordinates of the main interior points (offset from the exterior surface)
    Xa = o[0] + wallThickness
    Xb = o[0] + x - wallThickness
    Ya = o[1] + wallThickness
    Yb = o[1] + y - wallThickness

    #-- XML tree
    lod2Solid = etree.SubElement(bldg, "{%s}lod2Solid" % ns_bldg)
    MultiSolid = etree.SubElement(lod2Solid, "{%s}MultiSolid" % ns_gml)

    #-- Construct a solid for each floor
    for floor in range(1, int(floors) + 1):
        #-- Floor elevation
        fel = (floor - 1) * floorHeight + 0.5*joist
        #-- Ceiling elevation
        cel = floor * floorHeight - 0.5*joist

        #-- Add solids of the multisolid
        Solid = etree.SubElement(MultiSolid, "{%s}Solid" % ns_gml)
        if ASSIGNID:
            Solid.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
        exterior = etree.SubElement(Solid, "{%s}exterior" % ns_gml)
        CompositeSurface = etree.SubElement(exterior, "{%s}CompositeSurface" % ns_gml)
        #-- The eight points of the solid. F=Floor, C=Ceiling
        p0F = str(Xa) + ' ' + str(Ya) + ' ' + str(fel)
        p0C = str(Xa) + ' ' + str(Ya) + ' ' + str(cel)
        p1F = str(Xb) + ' ' + str(Ya) + ' ' + str(fel)
        p1C = str(Xb) + ' ' + str(Ya) + ' ' + str(cel)
        p2F = str(Xb) + ' ' + str(Yb) + ' ' + str(fel)
        p2C = str(Xb) + ' ' + str(Yb) + ' ' + str(cel)
        p3F = str(Xa) + ' ' + str(Yb) + ' ' + str(fel)
        p3C = str(Xa) + ' ' + str(Yb) + ' ' + str(cel)
        if floor == 1:
            if buildingpart is not None:
                if buildingpart['type'] == 'Alcove':
                    bp = [None] * 8
                    bp[0] = GMLPointList([o[0] + x - wallThickness, aux['origin'][1] + buildingpart['o'] + wallThickness, aux['origin'][2] + 0.5*joist])
                    bp[1] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']) - wallThickness, aux['origin'][1] + buildingpart['o'] + wallThickness, aux['origin'][2] + 0.5*joist])
                    bp[2] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']) - wallThickness, aux['origin'][1] + buildingpart['o'] + buildingpart['y'] - wallThickness, aux['origin'][2] + 0.5*joist])
                    bp[3] = GMLPointList([o[0] + x - wallThickness, aux['origin'][1] + buildingpart['o'] + buildingpart['y'] - wallThickness, aux['origin'][2] + 0.5*joist])
                    bp[4] = GMLPointList([o[0] + x - wallThickness, aux['origin'][1] + buildingpart['o'] + wallThickness, aux['origin'][2] + buildingpart['z'] - 0.5*joist])
                    bp[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']) - wallThickness, aux['origin'][1] + buildingpart['o'] + wallThickness, aux['origin'][2] + buildingpart['z'] - 0.5*joist])
                    bp[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']) - wallThickness, aux['origin'][1] + buildingpart['o'] + buildingpart['y'] - wallThickness, aux['origin'][2] + buildingpart['z'] - 0.5*joist])
                    bp[7] = GMLPointList([o[0] + x - wallThickness, aux['origin'][1] + buildingpart['o'] + buildingpart['y'] - wallThickness, aux['origin'][2] + buildingpart['z'] - 0.5*joist])
                    E = "%s %s %s %s %s %s %s %s %s" % (p1F, bp[0], bp[4], bp[7], bp[3], p2F, p2C, p1C, p1F)
                    faceBottom = "%s %s %s %s %s %s %s %s %s" % (p0F, p3F, p2F, bp[3], bp[2], bp[1], bp[0], p1F, p0F)
                    gface0 = "%s %s %s %s %s" % (bp[0], bp[1], bp[5], bp[4], bp[0])
                    gface1 = "%s %s %s %s %s" % (bp[1], bp[2], bp[6], bp[5], bp[1])
                    gface3 = "%s %s %s %s %s" % (bp[3], bp[7], bp[6], bp[2], bp[3])
                    gtop = "%s %s %s %s %s" % (bp[4], bp[5], bp[6], bp[7], bp[4])
                    addsurface(False, CompositeSurface, gface0)
                    addsurface(False, CompositeSurface, gface1)
                    addsurface(False, CompositeSurface, gface3)
                    addsurface(False, CompositeSurface, gtop)
                    top = "%s %s %s %s %s %s %s %s %s" % (p0C, p1C, bp[4], bp[5], bp[6], bp[7], p2C, p3C, p0C)
                elif buildingpart['type'] == 'Garage':
                    GarageSolid = etree.SubElement(MultiSolid, "{%s}Solid" % ns_gml)
                    GarageExterior = etree.SubElement(GarageSolid, "{%s}exterior" % ns_gml)
                    GarageCompositeSurface = etree.SubElement(GarageExterior, "{%s}CompositeSurface" % ns_gml)
                    E = "%s %s %s %s %s" % (p1F, p2F, p2C, p1C, p1F)
                    faceBottom = "%s %s %s %s %s" % (p0F, p3F, p2F, p1F, p0F)
                    top = "%s %s %s %s %s" % (p0C, p1C, p2C, p3C, p0C)
                    bp = [None] * 8
                    bp[0] = GMLPointList([o[0] + x + 0.0, aux['origin'][1] + buildingpart['o'] + wallThickness, aux['origin'][2] + 0.5*joist])
                    bp[1] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']) - wallThickness, aux['origin'][1] + buildingpart['o'] + wallThickness, aux['origin'][2] + 0.5*joist])
                    bp[2] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']) - wallThickness, aux['origin'][1] + buildingpart['o'] + buildingpart['y'] - wallThickness, aux['origin'][2] + 0.5*joist])
                    bp[3] = GMLPointList([o[0] + x + 0.0, aux['origin'][1] + buildingpart['o'] + buildingpart['y'] - wallThickness, aux['origin'][2] + 0.5*joist])
                    bp[4] = GMLPointList([o[0] + x + 0.0, aux['origin'][1] + buildingpart['o'] + wallThickness, aux['origin'][2] + buildingpart['z'] - 0.5*joist])
                    bp[5] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']) - wallThickness, aux['origin'][1] + buildingpart['o'] + wallThickness, aux['origin'][2] + buildingpart['z'] - 0.5*joist])
                    bp[6] = GMLPointList([o[0] + x + buildingpart['x'] - .5*(x - aux['xsize']) - wallThickness, aux['origin'][1] + buildingpart['o'] + buildingpart['y'] - wallThickness, aux['origin'][2] + buildingpart['z'] - 0.5*joist])
                    bp[7] = GMLPointList([o[0] + x + 0.0, aux['origin'][1] + buildingpart['o'] + buildingpart['y'] - wallThickness, aux['origin'][2] + buildingpart['z'] - 0.5*joist])

                    gface0 = "%s %s %s %s %s" % (bp[0], bp[1], bp[5], bp[4], bp[0])
                    gface1 = "%s %s %s %s %s" % (bp[1], bp[2], bp[6], bp[5], bp[1])
                    gface2 = "%s %s %s %s %s" % (bp[0], bp[4], bp[7], bp[3], bp[0])
                    gface3 = "%s %s %s %s %s" % (bp[3], bp[7], bp[6], bp[2], bp[3])
                    gtop = "%s %s %s %s %s" % (bp[4], bp[5], bp[6], bp[7], bp[4])
                    gbottom = "%s %s %s %s %s" % (bp[0], bp[3], bp[2], bp[1], bp[0])
                    addsurface(False, GarageCompositeSurface, gface0)
                    addsurface(False, GarageCompositeSurface, gface1)
                    addsurface(False, GarageCompositeSurface, gface2)
                    addsurface(False, GarageCompositeSurface, gface3)
                    addsurface(False, GarageCompositeSurface, gtop)
                    addsurface(False, GarageCompositeSurface, gbottom)
            else:
                E = "%s %s %s %s %s" % (p1F, p2F, p2C, p1C, p1F)
                faceBottom = "%s %s %s %s %s" % (p0F, p3F, p2F, p1F, p0F)
                top = "%s %s %s %s %s" % (p0C, p1C, p2C, p3C, p0C)
        else:
            faceBottom = "%s %s %s %s %s" % (p0F, p3F, p2F, p1F, p0F)
            top = "%s %s %s %s %s" % (p0C, p1C, p2C, p3C, p0C)
            E = "%s %s %s %s %s" % (p1F, p2F, p2C, p1C, p1F)
        S = "%s %s %s %s %s" % (p0F, p1F, p1C, p0C, p0F)
        N = "%s %s %s %s %s" % (p2F, p3F, p3C, p2C, p2F)
        W = "%s %s %s %s %s" % (p3F, p0F, p0C, p3C, p3F)
        addsurface(False, CompositeSurface, faceBottom)
        addsurface(False, CompositeSurface, top)
        addsurface(False, CompositeSurface, S)
        addsurface(False, CompositeSurface, E)
        addsurface(False, CompositeSurface, N)
        addsurface(False, CompositeSurface, W)

        dormerTickness = .1
        if rtype != 'Flat':
            if rtype == 'Shed':
                h2 = (h/x) * (x - 2* wallThickness)
                topThickness = h - h2 - .5*joist
                #rWth = (topThickness/h)*(x)
                rWth = (topThickness/h)*(x) - wallThickness
                rWth2 = None
            elif rtype == 'Pyramidal' or rtype == 'Hipped':
                h2 = (h/(.5*x)) * (.5*x - wallThickness)
                topThickness = h - h2 - .5*joist
                rWth = (topThickness/h)*(.5*x)
                #rWth2 = (topThickness/h)*(width)
                # auxl1 = (topThickness*width)/h
                # rWth2 = topThickness**2 * auxl1
                rWth2 = wallThickness - ((width * .5*joist)/h)
            else:
                h2 = (h/(.5*x)) * (.5*x - wallThickness)
                topThickness = h - h2 - .5*joist
                rWth = (topThickness/h)*(.5*x)
                rWth2 = None

        p = verticesBody(o, x, y, z)
        pList = verticesBodyList(o, x, y, z)
        ropenings = [[], [], [], []]
        if dormers and len(dormers) > 0:
            for drm in dormers:
                #-- Get a list of vertices of each dormer
                dList, dListGML = interiordormerVertices([drm], pList, h, rtype, [o, x, y, z], width, wallThickness, rWth, dormerTickness, topThickness, rWth2)
                #-- Get the opening for creating a hole in the roof surface
                ropenings[int(drm['side'])].append(str(dListGML[0][0] + ' ' + dListGML[0][3] + ' ' + dListGML[0][2] + ' ' + dListGML[0][1] + ' ' + dListGML[0][0]))
                interiorDormer(CompositeSurface, [dList[0], dListGML[0]], drm['side'])    

    #-- Solid for the attic
    if rtype != 'Flat':

        XTa = o[0] + wallThickness
        XTb = o[0] + x - wallThickness
        YTa = o[1] + wallThickness
        YTb = o[1] + y - wallThickness

        r = verticesRoof([o, x, y, z], h, rtype, width)
        r[0] = GMLstring2points(r[0])[0]
        r[1] = GMLstring2points(r[1])[0]
        #-- Floor elevation
        fel = floors * floorHeight + 0.5*joist
        #-- Ceiling elevation of the roof. Requires some computations to preserve parallel walls

        cel = float(r[0][2]) - topThickness
        #-- XML tree
        # lod2Solid = etree.SubElement(bldg, "{%s}lod2Solid" % ns_bldg)
        Solid = etree.SubElement(MultiSolid, "{%s}Solid" % ns_gml)
        if ASSIGNID:
            Solid.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
        exterior = etree.SubElement(Solid, "{%s}exterior" % ns_gml)
        CompositeSurface = etree.SubElement(exterior, "{%s}CompositeSurface" % ns_gml)
        if rtype == 'Gabled':
            gabledAttic(CompositeSurface, [XTa, YTa, XTb, YTb], p, r, fel, cel, wallThickness, topThickness, True, ropenings)

        elif rtype == 'Hipped':

            hippedAttic(CompositeSurface, [XTa, YTa, XTb, YTb], p, r, fel, cel, wallThickness, topThickness, True, ropenings)
                #addsurface(False, CompositeSurface, aS)
        elif rtype == 'Pyramidal':
            pyramidalAttic(CompositeSurface, [XTa, YTa, XTb, YTb], p, r, fel, cel, wallThickness, topThickness, True, ropenings)

        elif rtype == 'Shed':
            shedAttic(CompositeSurface, [XTa, YTa, XTb, YTb], p, r, fel, cel, wallThickness, topThickness, True, ropenings)


def b2p(exts):
    """Convert two points of a polygon into its bounding box.
    (Rectangular polygon parallel with axes.)
    """
    p0x = exts[0][0]
    p0y = exts[0][1]
    p0 = str(p0x) + ' ' + str(p0y) + ' ' + '0.0' 
    p1x = exts[0][2]
    p1y = exts[0][3]
    p1 = str(p1x) + ' ' + str(p1y) + ' ' + '0.0'
    pb = str(p1x) + ' ' + str(p0y) + ' ' + '0.0' 
    pu = str(p0x) + ' ' + str(p1y) + ' ' + '0.0' 
    e = "%s %s %s %s %s" % (p0, pb, p1, pu, p0)
    i = []
    if exts[1] is not None:
        for h in exts[1]:
            p0x = h[0]
            p0y = h[1]
            p0 = str(p0x) + ' ' + str(p0y) + ' ' + '0.0' 
            p1x = h[2]
            p1y = h[3]
            p1 = str(p1x) + ' ' + str(p1y) + ' ' + '0.0'
            pb = str(p1x) + ' ' + str(p0y) + ' ' + '0.0' 
            pu = str(p0x) + ' ' + str(p1y) + ' ' + '0.0' 
            i.append("%s %s %s %s %s" % (p0, pu, p1, pb, p0))
    return e, i


def b2s(exts):
    """Convert two points of a solid into its bounding box.
    (Cube-like solid parallel with axes.)
    """
    p0x = exts[0][0]
    p0y = exts[0][1]
    p0 = str(p0x) + ' ' + str(p0y) + ' ' + '0.0' 
    p0T = str(p0x) + ' ' + str(p0y) + ' ' + str(exts[1])

    p1x = exts[0][2]
    p1y = exts[0][3]
    p1 = str(p1x) + ' ' + str(p1y) + ' ' + '0.0'
    p1T = str(p1x) + ' ' + str(p1y) + ' ' + str(exts[1])

    pb = str(p1x) + ' ' + str(p0y) + ' ' + '0.0' 
    pbT = str(p1x) + ' ' + str(p0y) + ' ' + str(exts[1])
    pu = str(p0x) + ' ' + str(p1y) + ' ' + '0.0' 
    puT = str(p0x) + ' ' + str(p1y) + ' ' + str(exts[1])

    surfaces = []
    surfaces.append("%s %s %s %s %s" % (p0, pu, p1, pb, p0))
    surfaces.append("%s %s %s %s %s" % (p0T, pbT, p1T, puT, p0T))
    surfaces.append("%s %s %s %s %s" % (p0, pb, pbT, p0T, p0))
    surfaces.append("%s %s %s %s %s" % (pb, p1, p1T, pbT, pb))
    surfaces.append("%s %s %s %s %s" % (p1, pu, puT, p1T, p1))
    surfaces.append("%s %s %s %s %s" % (pu, p0, p0T, puT, pu))

    return surfaces


def CityGMLstreets(CityModel, street_data):
    """Generates a road network with the thematic module for Transportation Objects."""
    cityObject = etree.SubElement(CityModel, "cityObjectMember")
    transpobj = etree.SubElement(cityObject, "{%s}Road" % ns_tran)
    if ASSIGNID:
        transpobj.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
    transpms = etree.SubElement(transpobj, "{%s}lod1MultiSurface" % ns_tran)
    MultiSurface = etree.SubElement(transpms, "{%s}MultiSurface" % ns_gml)
    surfaceMember = etree.SubElement(MultiSurface, "{%s}surfaceMember" % ns_gml)
    Polygon = etree.SubElement(surfaceMember, "{%s}Polygon" % ns_gml)
    if ASSIGNID:
        Polygon.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())

    street_points = b2p(street_data)

    PolygonExterior = etree.SubElement(Polygon, "{%s}exterior" % ns_gml)
    LinearRing = etree.SubElement(PolygonExterior, "{%s}LinearRing" % ns_gml)
    posList = etree.SubElement(LinearRing, "{%s}posList" % ns_gml)
    posList.text = street_points[0]

    for h in street_points[1]:
        PolygonInterior = etree.SubElement(Polygon, "{%s}interior" % ns_gml)
        LinearRing = etree.SubElement(PolygonInterior, "{%s}LinearRing" % ns_gml)
        posList = etree.SubElement(LinearRing, "{%s}posList" % ns_gml)
        posList.text = h


def CityGMLplantCoverLOD0(CityModel, pc_data):
    """Generates a PlantCover as a 2.5D surface."""
    cityObject = etree.SubElement(CityModel, "cityObjectMember")
    pcobj = etree.SubElement(cityObject, "{%s}PlantCover" % ns_veg)
    if ASSIGNID:
        pcobj.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
    pcms = etree.SubElement(pcobj, "{%s}lod1MultiSurface" % ns_veg)
    MultiSurface = etree.SubElement(pcms, "{%s}MultiSurface" % ns_gml)
    surfaceMember = etree.SubElement(MultiSurface, "{%s}surfaceMember" % ns_gml)
    Polygon = etree.SubElement(surfaceMember, "{%s}Polygon" % ns_gml)
    if ASSIGNID:
        Polygon.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())

    pc_points = b2p([pc_data[0], None])

    PolygonExterior = etree.SubElement(Polygon, "{%s}exterior" % ns_gml)
    LinearRing = etree.SubElement(PolygonExterior, "{%s}LinearRing" % ns_gml)
    posList = etree.SubElement(LinearRing, "{%s}posList" % ns_gml)
    posList.text = pc_points[0]


def CityGMLplantCoverLOD1(CityModel, pc_data):
    """Generates a PlantCover as a solid."""
    cityObject = etree.SubElement(CityModel, "cityObjectMember")
    pcobj = etree.SubElement(cityObject, "{%s}PlantCover" % ns_veg)
    if ASSIGNID:
        pcobj.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
    lod1MultiSolid = etree.SubElement(pcobj, "{%s}lod1MultiSolid" % ns_veg)
    multiSolid = etree.SubElement(lod1MultiSolid, "{%s}MultiSolid" % ns_gml)
    solidmember = etree.SubElement(multiSolid, "{%s}solidMember" % ns_gml)
    Solid = etree.SubElement(solidmember, "{%s}Solid" % ns_gml)
    if ASSIGNID:
        Solid.attrib['{%s}id' % ns_gml] = str(uuid.uuid4())
    exterior = etree.SubElement(Solid, "{%s}exterior" % ns_gml)
    CompositeSurface = etree.SubElement(exterior, "{%s}CompositeSurface" % ns_gml)
    
    pc_surfaces = b2s(pc_data)

    for pc_s in pc_surfaces:
        addsurface(False, CompositeSurface, pc_s)


def rotator(vertex, sine, cos, origin_of_rotation):
    "Rotate the vertex around the origin by an angle (2D). Cos and sin are already precomputed to make the calculations more efficient due to many repetitions."
    vertex = [float(vertex[0]), float(vertex[1]), float(vertex[2])]
    rotated = [None, None, vertex[2]]
    rotated[0] = ((vertex[0]-origin_of_rotation[0]) * cos - (vertex[1]-origin_of_rotation[1]) * sine) + origin_of_rotation[0]
    rotated[1] = ((vertex[0]-origin_of_rotation[0]) * sine + (vertex[1]-origin_of_rotation[1]) * cos) + origin_of_rotation[1]
    return rotated

#----------------------------------------------------------------------
#-- Start of the program
print('Parsing file', BUILDINGFILE, '...')

#-- Parse the file containing the building information
BUILDINGFILE = etree.parse(BUILDINGFILE)
root = BUILDINGFILE.getroot()
#-- Buildings will be stored here
buildings = []
#-- Streets will be stored here
streets = []
#-- PlantCover will be stored here
plantcover = []

#-- Find all instances of city objects in the XML and put them in a list
for obj in root.getiterator('building'):
    buildings.append(obj)
for obj in root.getiterator('streets'):
    streets.append(obj)
for obj in root.getiterator('parks'):
    plantcover.append(obj)

print("There are", len(buildings), "buildings(s) in this XML. Processing...")

print("Opening empty CityGML files...")
CityGMLs = {}

#-- Instances

## LOD0

#-- LOD0.0
CityGMLs['LOD0_0'] = createCityGML('LOD0_0')

#-- LOD0.1
if VARIANTS:
    CityGMLs['LOD0_1_F0_H0'] = createCityGML('LOD0_1_F0_H0')
    CityGMLs['LOD0_1_F0_H1'] = createCityGML('LOD0_1_F0_H1')
    CityGMLs['LOD0_1_F0_H2'] = createCityGML('LOD0_1_F0_H2')

CityGMLs['LOD0_1_F0_H3'] = createCityGML('LOD0_1_F0_H3')

if VARIANTS:
    CityGMLs['LOD0_1_F0_H4'] = createCityGML('LOD0_1_F0_H4')
    CityGMLs['LOD0_1_F0_H5'] = createCityGML('LOD0_1_F0_H5')
    CityGMLs['LOD0_1_F0_H6'] = createCityGML('LOD0_1_F0_H6')
    CityGMLs['LOD0_1_F0_HAvg'] = createCityGML('LOD0_1_F0_HAvg')
    CityGMLs['LOD0_1_F0_HMed'] = createCityGML('LOD0_1_F0_HMed')

if VARIANTS:
    CityGMLs['LOD0_1_F1_H0'] = createCityGML('LOD0_1_F1_H0')
    CityGMLs['LOD0_1_F1_H1'] = createCityGML('LOD0_1_F1_H1')
    CityGMLs['LOD0_1_F1_H2'] = createCityGML('LOD0_1_F1_H2')
    CityGMLs['LOD0_1_F1_H3'] = createCityGML('LOD0_1_F1_H3')
    CityGMLs['LOD0_1_F1_H4'] = createCityGML('LOD0_1_F1_H4')
    CityGMLs['LOD0_1_F1_H5'] = createCityGML('LOD0_1_F1_H5')
    CityGMLs['LOD0_1_F1_H6'] = createCityGML('LOD0_1_F1_H6')
    CityGMLs['LOD0_1_F1_HAvg'] = createCityGML('LOD0_1_F1_HAvg')
    CityGMLs['LOD0_1_F1_HMed'] = createCityGML('LOD0_1_F1_HMed')

if VARIANTS:
    CityGMLs['LOD0_1_Fd_H0'] = createCityGML('LOD0_1_Fd_H0')
    CityGMLs['LOD0_1_Fd_H1'] = createCityGML('LOD0_1_Fd_H1')
    CityGMLs['LOD0_1_Fd_H2'] = createCityGML('LOD0_1_Fd_H2')
    CityGMLs['LOD0_1_Fd_H3'] = createCityGML('LOD0_1_Fd_H3')
    CityGMLs['LOD0_1_Fd_H4'] = createCityGML('LOD0_1_Fd_H4')
    CityGMLs['LOD0_1_Fd_H5'] = createCityGML('LOD0_1_Fd_H5')
    CityGMLs['LOD0_1_Fd_H6'] = createCityGML('LOD0_1_Fd_H6')
    CityGMLs['LOD0_1_Fd_HAvg'] = createCityGML('LOD0_1_Fd_HAvg')
    CityGMLs['LOD0_1_Fd_HMed'] = createCityGML('LOD0_1_Fd_HMed')


#-- LOD0.2
if VARIANTS:
    CityGMLs['LOD0_2_F0_H0'] = createCityGML('LOD0_2_F0_H0')
    CityGMLs['LOD0_2_F0_H1'] = createCityGML('LOD0_2_F0_H1')
    CityGMLs['LOD0_2_F0_H2'] = createCityGML('LOD0_2_F0_H2')

CityGMLs['LOD0_2_F0_H3'] = createCityGML('LOD0_2_F0_H3')

if VARIANTS:
    CityGMLs['LOD0_2_F0_H4'] = createCityGML('LOD0_2_F0_H4')
    CityGMLs['LOD0_2_F0_H5'] = createCityGML('LOD0_2_F0_H5')
    CityGMLs['LOD0_2_F0_H6'] = createCityGML('LOD0_2_F0_H6')
    CityGMLs['LOD0_2_F0_HAvg'] = createCityGML('LOD0_2_F0_HAvg')
    CityGMLs['LOD0_2_F0_HMed'] = createCityGML('LOD0_2_F0_HMed')


if VARIANTS:
    CityGMLs['LOD0_2_F1_H0'] = createCityGML('LOD0_2_F1_H0')
    CityGMLs['LOD0_2_F1_H1'] = createCityGML('LOD0_2_F1_H1')
    CityGMLs['LOD0_2_F1_H2'] = createCityGML('LOD0_2_F1_H2')
    CityGMLs['LOD0_2_F1_H3'] = createCityGML('LOD0_2_F1_H3')
    CityGMLs['LOD0_2_F1_H4'] = createCityGML('LOD0_2_F1_H4')
    CityGMLs['LOD0_2_F1_H5'] = createCityGML('LOD0_2_F1_H5')
    CityGMLs['LOD0_2_F1_H6'] = createCityGML('LOD0_2_F1_H6')
    CityGMLs['LOD0_2_F1_HAvg'] = createCityGML('LOD0_2_F1_HAvg')
    CityGMLs['LOD0_2_F1_HMed'] = createCityGML('LOD0_2_F1_HMed')

if VARIANTS:
    CityGMLs['LOD0_2_Fd_H0'] = createCityGML('LOD0_2_Fd_H0')
    CityGMLs['LOD0_2_Fd_H1'] = createCityGML('LOD0_2_Fd_H1')
    CityGMLs['LOD0_2_Fd_H2'] = createCityGML('LOD0_2_Fd_H2')
    CityGMLs['LOD0_2_Fd_H3'] = createCityGML('LOD0_2_Fd_H3')
    CityGMLs['LOD0_2_Fd_H4'] = createCityGML('LOD0_2_Fd_H4')
    CityGMLs['LOD0_2_Fd_H5'] = createCityGML('LOD0_2_Fd_H5')
    CityGMLs['LOD0_2_Fd_H6'] = createCityGML('LOD0_2_Fd_H6')
    CityGMLs['LOD0_2_Fd_HAvg'] = createCityGML('LOD0_2_Fd_HAvg')
    CityGMLs['LOD0_2_Fd_HMed'] = createCityGML('LOD0_2_Fd_HMed')

#-- LOD0.3
if VARIANTS:
    CityGMLs['LOD0_3_F0_H0'] = createCityGML('LOD0_3_F0_H0')
    CityGMLs['LOD0_3_F0_H1'] = createCityGML('LOD0_3_F0_H1')
    CityGMLs['LOD0_3_F0_H2'] = createCityGML('LOD0_3_F0_H2')

CityGMLs['LOD0_3_F0_H3'] = createCityGML('LOD0_3_F0_H3')

if VARIANTS:
    CityGMLs['LOD0_3_F0_H4'] = createCityGML('LOD0_3_F0_H4')
    CityGMLs['LOD0_3_F0_H5'] = createCityGML('LOD0_3_F0_H5')
    CityGMLs['LOD0_3_F0_H6'] = createCityGML('LOD0_3_F0_H6')
    CityGMLs['LOD0_3_F0_HAvg'] = createCityGML('LOD0_3_F0_HAvg')
    CityGMLs['LOD0_3_F0_HMed'] = createCityGML('LOD0_3_F0_HMed')

if VARIANTS:
    CityGMLs['LOD0_3_F1_H0'] = createCityGML('LOD0_3_F1_H0')
    CityGMLs['LOD0_3_F1_H1'] = createCityGML('LOD0_3_F1_H1')
    CityGMLs['LOD0_3_F1_H2'] = createCityGML('LOD0_3_F1_H2')
    CityGMLs['LOD0_3_F1_H3'] = createCityGML('LOD0_3_F1_H3')
    CityGMLs['LOD0_3_F1_H4'] = createCityGML('LOD0_3_F1_H4')
    CityGMLs['LOD0_3_F1_H5'] = createCityGML('LOD0_3_F1_H5')
    CityGMLs['LOD0_3_F1_H6'] = createCityGML('LOD0_3_F1_H6')
    CityGMLs['LOD0_3_F1_HAvg'] = createCityGML('LOD0_3_F1_HAvg')
    CityGMLs['LOD0_3_F1_HMed'] = createCityGML('LOD0_3_F1_HMed')

if VARIANTS:
    CityGMLs['LOD0_3_Fd_H0'] = createCityGML('LOD0_3_Fd_H0')
    CityGMLs['LOD0_3_Fd_H1'] = createCityGML('LOD0_3_Fd_H1')
    CityGMLs['LOD0_3_Fd_H2'] = createCityGML('LOD0_3_Fd_H2')
    CityGMLs['LOD0_3_Fd_H3'] = createCityGML('LOD0_3_Fd_H3')
    CityGMLs['LOD0_3_Fd_H4'] = createCityGML('LOD0_3_Fd_H4')
    CityGMLs['LOD0_3_Fd_H5'] = createCityGML('LOD0_3_Fd_H5')
    CityGMLs['LOD0_3_Fd_H6'] = createCityGML('LOD0_3_Fd_H6')
    CityGMLs['LOD0_3_Fd_HAvg'] = createCityGML('LOD0_3_Fd_HAvg')
    CityGMLs['LOD0_3_Fd_HMed'] = createCityGML('LOD0_3_Fd_HMed')

## LOD1

#-- LOD1.0
CityGMLs['LOD1_0_HMin'] = createCityGML('LOD1_0_HMin')
if SOLIDS:
    CityGMLs['LOD1_0_HMin_solid'] = createCityGML('LOD1_0_HMin_solid')
    CityGMLs['LOD1_0_HMin_semantics'] = createCityGML('LOD1_0_HMin_semantics')

if VARIANTS:
    CityGMLs['LOD1_0_HAvg'] = createCityGML('LOD1_0_HAvg')
    if SOLIDS:
        CityGMLs['LOD1_0_HAvg_solid'] = createCityGML('LOD1_0_HAvg_solid')
        CityGMLs['LOD1_0_HAvg_semantics'] = createCityGML('LOD1_0_HAvg_semantics')

    CityGMLs['LOD1_0_HMax'] = createCityGML('LOD1_0_HMax')
    if SOLIDS:
        CityGMLs['LOD1_0_HMax_solid'] = createCityGML('LOD1_0_HMax_solid')
        CityGMLs['LOD1_0_HMax_semantics'] = createCityGML('LOD1_0_HMax_semantics')

    CityGMLs['LOD1_0_HMedian'] = createCityGML('LOD1_0_HMedian')
    if SOLIDS:
        CityGMLs['LOD1_0_HMedian_solid'] = createCityGML('LOD1_0_HMedian_solid')
        CityGMLs['LOD1_0_HMedian_semantics'] = createCityGML('LOD1_0_HMedian_semantics')

#-- LOD1.1
if VARIANTS:
    CityGMLs['LOD1_1_F0_H0'] = createCityGML('LOD1_1_F0_H0')
    CityGMLs['LOD1_1_F0_H1'] = createCityGML('LOD1_1_F0_H1')
    CityGMLs['LOD1_1_F0_H2'] = createCityGML('LOD1_1_F0_H2')

CityGMLs['LOD1_1_F0_H3'] = createCityGML('LOD1_1_F0_H3')

if VARIANTS:
    CityGMLs['LOD1_1_F0_H4'] = createCityGML('LOD1_1_F0_H4')
    CityGMLs['LOD1_1_F0_H5'] = createCityGML('LOD1_1_F0_H5')
    CityGMLs['LOD1_1_F0_H6'] = createCityGML('LOD1_1_F0_H6')
    CityGMLs['LOD1_1_F0_HAvg'] = createCityGML('LOD1_1_F0_HAvg')
    CityGMLs['LOD1_1_F0_HMed'] = createCityGML('LOD1_1_F0_HMed')

if VARIANTS:
    CityGMLs['LOD1_1_F1_H0'] = createCityGML('LOD1_1_F1_H0')
    CityGMLs['LOD1_1_F1_H1'] = createCityGML('LOD1_1_F1_H1')
    CityGMLs['LOD1_1_F1_H2'] = createCityGML('LOD1_1_F1_H2')
    CityGMLs['LOD1_1_F1_H3'] = createCityGML('LOD1_1_F1_H3')
    CityGMLs['LOD1_1_F1_H4'] = createCityGML('LOD1_1_F1_H4')
    CityGMLs['LOD1_1_F1_H5'] = createCityGML('LOD1_1_F1_H5')
    CityGMLs['LOD1_1_F1_H6'] = createCityGML('LOD1_1_F1_H6')
    CityGMLs['LOD1_1_F1_HAvg'] = createCityGML('LOD1_1_F1_HAvg')
    CityGMLs['LOD1_1_F1_HMed'] = createCityGML('LOD1_1_F1_HMed')

if VARIANTS:
    CityGMLs['LOD1_1_Fd_H0'] = createCityGML('LOD1_1_Fd_H0')
    CityGMLs['LOD1_1_Fd_H1'] = createCityGML('LOD1_1_Fd_H1')
    CityGMLs['LOD1_1_Fd_H2'] = createCityGML('LOD1_1_Fd_H2')
    CityGMLs['LOD1_1_Fd_H3'] = createCityGML('LOD1_1_Fd_H3')
    CityGMLs['LOD1_1_Fd_H4'] = createCityGML('LOD1_1_Fd_H4')
    CityGMLs['LOD1_1_Fd_H5'] = createCityGML('LOD1_1_Fd_H5')
    CityGMLs['LOD1_1_Fd_H6'] = createCityGML('LOD1_1_Fd_H6')
    CityGMLs['LOD1_1_Fd_HAvg'] = createCityGML('LOD1_1_Fd_HAvg')
    CityGMLs['LOD1_1_Fd_HMed'] = createCityGML('LOD1_1_Fd_HMed')

if SOLIDS:
    if VARIANTS:
        CityGMLs['LOD1_1_F0_H0_solid'] = createCityGML('LOD1_1_F0_H0_solid')
        CityGMLs['LOD1_1_F0_H1_solid'] = createCityGML('LOD1_1_F0_H1_solid')
        CityGMLs['LOD1_1_F0_H2_solid'] = createCityGML('LOD1_1_F0_H2_solid')

    CityGMLs['LOD1_1_F0_H3_solid'] = createCityGML('LOD1_1_F0_H3_solid')

    if VARIANTS:
        CityGMLs['LOD1_1_F0_H4_solid'] = createCityGML('LOD1_1_F0_H4_solid')
        CityGMLs['LOD1_1_F0_H5_solid'] = createCityGML('LOD1_1_F0_H5_solid')
        CityGMLs['LOD1_1_F0_H6_solid'] = createCityGML('LOD1_1_F0_H6_solid')
        CityGMLs['LOD1_1_F0_HAvg_solid'] = createCityGML('LOD1_1_F0_HAvg_solid')
        CityGMLs['LOD1_1_F0_HMed_solid'] = createCityGML('LOD1_1_F0_HMed_solid')

    if VARIANTS:
        CityGMLs['LOD1_1_F1_H0_solid'] = createCityGML('LOD1_1_F1_H0_solid')
        CityGMLs['LOD1_1_F1_H1_solid'] = createCityGML('LOD1_1_F1_H1_solid')
        CityGMLs['LOD1_1_F1_H2_solid'] = createCityGML('LOD1_1_F1_H2_solid')
        CityGMLs['LOD1_1_F1_H3_solid'] = createCityGML('LOD1_1_F1_H3_solid')
        CityGMLs['LOD1_1_F1_H4_solid'] = createCityGML('LOD1_1_F1_H4_solid')
        CityGMLs['LOD1_1_F1_H5_solid'] = createCityGML('LOD1_1_F1_H5_solid')
        CityGMLs['LOD1_1_F1_H6_solid'] = createCityGML('LOD1_1_F1_H6_solid')
        CityGMLs['LOD1_1_F1_HAvg_solid'] = createCityGML('LOD1_1_F1_HAvg_solid')
        CityGMLs['LOD1_1_F1_HMed_solid'] = createCityGML('LOD1_1_F1_HMed_solid')

    if VARIANTS:
        CityGMLs['LOD1_1_Fd_H0_solid'] = createCityGML('LOD1_1_Fd_H0_solid')
        CityGMLs['LOD1_1_Fd_H1_solid'] = createCityGML('LOD1_1_Fd_H1_solid')
        CityGMLs['LOD1_1_Fd_H2_solid'] = createCityGML('LOD1_1_Fd_H2_solid')
        CityGMLs['LOD1_1_Fd_H3_solid'] = createCityGML('LOD1_1_Fd_H3_solid')
        CityGMLs['LOD1_1_Fd_H4_solid'] = createCityGML('LOD1_1_Fd_H4_solid')
        CityGMLs['LOD1_1_Fd_H5_solid'] = createCityGML('LOD1_1_Fd_H5_solid')
        CityGMLs['LOD1_1_Fd_H6_solid'] = createCityGML('LOD1_1_Fd_H6_solid')
        CityGMLs['LOD1_1_Fd_HAvg_solid'] = createCityGML('LOD1_1_Fd_HAvg_solid')
        CityGMLs['LOD1_1_Fd_HMed_solid'] = createCityGML('LOD1_1_Fd_HMed_solid')

    if VARIANTS:
        CityGMLs['LOD1_1_F0_H0_semantics'] = createCityGML('LOD1_1_F0_H0_semantics')
        CityGMLs['LOD1_1_F0_H1_semantics'] = createCityGML('LOD1_1_F0_H1_semantics')
        CityGMLs['LOD1_1_F0_H2_semantics'] = createCityGML('LOD1_1_F0_H2_semantics')

    CityGMLs['LOD1_1_F0_H3_semantics'] = createCityGML('LOD1_1_F0_H3_semantics')

    if VARIANTS:
        CityGMLs['LOD1_1_F0_H4_semantics'] = createCityGML('LOD1_1_F0_H4_semantics')
        CityGMLs['LOD1_1_F0_H5_semantics'] = createCityGML('LOD1_1_F0_H5_semantics')
        CityGMLs['LOD1_1_F0_H6_semantics'] = createCityGML('LOD1_1_F0_H6_semantics')
        CityGMLs['LOD1_1_F0_HAvg_semantics'] = createCityGML('LOD1_1_F0_HAvg_semantics')
        CityGMLs['LOD1_1_F0_HMed_semantics'] = createCityGML('LOD1_1_F0_HMed_semantics')

    if VARIANTS:
        CityGMLs['LOD1_1_F1_H0_semantics'] = createCityGML('LOD1_1_F1_H0_semantics')
        CityGMLs['LOD1_1_F1_H1_semantics'] = createCityGML('LOD1_1_F1_H1_semantics')
        CityGMLs['LOD1_1_F1_H2_semantics'] = createCityGML('LOD1_1_F1_H2_semantics')
        CityGMLs['LOD1_1_F1_H3_semantics'] = createCityGML('LOD1_1_F1_H3_semantics')
        CityGMLs['LOD1_1_F1_H4_semantics'] = createCityGML('LOD1_1_F1_H4_semantics')
        CityGMLs['LOD1_1_F1_H5_semantics'] = createCityGML('LOD1_1_F1_H5_semantics')
        CityGMLs['LOD1_1_F1_H6_semantics'] = createCityGML('LOD1_1_F1_H6_semantics')
        CityGMLs['LOD1_1_F1_HAvg_semantics'] = createCityGML('LOD1_1_F1_HAvg_semantics')
        CityGMLs['LOD1_1_F1_HMed_semantics'] = createCityGML('LOD1_1_F1_HMed_semantics')

    if VARIANTS:
        CityGMLs['LOD1_1_Fd_H0_semantics'] = createCityGML('LOD1_1_Fd_H0_semantics')
        CityGMLs['LOD1_1_Fd_H1_semantics'] = createCityGML('LOD1_1_Fd_H1_semantics')
        CityGMLs['LOD1_1_Fd_H2_semantics'] = createCityGML('LOD1_1_Fd_H2_semantics')
        CityGMLs['LOD1_1_Fd_H3_semantics'] = createCityGML('LOD1_1_Fd_H3_semantics')
        CityGMLs['LOD1_1_Fd_H4_semantics'] = createCityGML('LOD1_1_Fd_H4_semantics')
        CityGMLs['LOD1_1_Fd_H5_semantics'] = createCityGML('LOD1_1_Fd_H5_semantics')
        CityGMLs['LOD1_1_Fd_H6_semantics'] = createCityGML('LOD1_1_Fd_H6_semantics')
        CityGMLs['LOD1_1_Fd_HAvg_semantics'] = createCityGML('LOD1_1_Fd_HAvg_semantics')
        CityGMLs['LOD1_1_Fd_HMed_semantics'] = createCityGML('LOD1_1_Fd_HMed_semantics')


#-- LOD1.2
if VARIANTS:
    CityGMLs['LOD1_2_F0_H0'] = createCityGML('LOD1_2_F0_H0')
    CityGMLs['LOD1_2_F0_H1'] = createCityGML('LOD1_2_F0_H1')
    CityGMLs['LOD1_2_F0_H2'] = createCityGML('LOD1_2_F0_H2')

CityGMLs['LOD1_2_F0_H3'] = createCityGML('LOD1_2_F0_H3')

if VARIANTS:
    CityGMLs['LOD1_2_F0_H4'] = createCityGML('LOD1_2_F0_H4')
    CityGMLs['LOD1_2_F0_H5'] = createCityGML('LOD1_2_F0_H5')
    CityGMLs['LOD1_2_F0_H6'] = createCityGML('LOD1_2_F0_H6')
    CityGMLs['LOD1_2_F0_HAvg'] = createCityGML('LOD1_2_F0_HAvg')
    CityGMLs['LOD1_2_F0_HMed'] = createCityGML('LOD1_2_F0_HMed')

if VARIANTS:
    CityGMLs['LOD1_2_F1_H0'] = createCityGML('LOD1_2_F1_H0')
    CityGMLs['LOD1_2_F1_H1'] = createCityGML('LOD1_2_F1_H1')
    CityGMLs['LOD1_2_F1_H2'] = createCityGML('LOD1_2_F1_H2')
    CityGMLs['LOD1_2_F1_H3'] = createCityGML('LOD1_2_F1_H3')
    CityGMLs['LOD1_2_F1_H4'] = createCityGML('LOD1_2_F1_H4')
    CityGMLs['LOD1_2_F1_H5'] = createCityGML('LOD1_2_F1_H5')
    CityGMLs['LOD1_2_F1_H6'] = createCityGML('LOD1_2_F1_H6')
    CityGMLs['LOD1_2_F1_HAvg'] = createCityGML('LOD1_2_F1_HAvg')
    CityGMLs['LOD1_2_F1_HMed'] = createCityGML('LOD1_2_F1_HMed')

if VARIANTS:
    CityGMLs['LOD1_2_Fd_H0'] = createCityGML('LOD1_2_Fd_H0')
    CityGMLs['LOD1_2_Fd_H1'] = createCityGML('LOD1_2_Fd_H1')
    CityGMLs['LOD1_2_Fd_H2'] = createCityGML('LOD1_2_Fd_H2')
    CityGMLs['LOD1_2_Fd_H3'] = createCityGML('LOD1_2_Fd_H3')
    CityGMLs['LOD1_2_Fd_H4'] = createCityGML('LOD1_2_Fd_H4')
    CityGMLs['LOD1_2_Fd_H5'] = createCityGML('LOD1_2_Fd_H5')
    CityGMLs['LOD1_2_Fd_H6'] = createCityGML('LOD1_2_Fd_H6')
    CityGMLs['LOD1_2_Fd_HAvg'] = createCityGML('LOD1_2_Fd_HAvg')
    CityGMLs['LOD1_2_Fd_HMed'] = createCityGML('LOD1_2_Fd_HMed')


if SOLIDS:
    if VARIANTS:
        CityGMLs['LOD1_2_F0_H0_solid'] = createCityGML('LOD1_2_F0_H0_solid')
        CityGMLs['LOD1_2_F0_H1_solid'] = createCityGML('LOD1_2_F0_H1_solid')
        CityGMLs['LOD1_2_F0_H2_solid'] = createCityGML('LOD1_2_F0_H2_solid')

    CityGMLs['LOD1_2_F0_H3_solid'] = createCityGML('LOD1_2_F0_H3_solid')

    if VARIANTS:
        CityGMLs['LOD1_2_F0_H4_solid'] = createCityGML('LOD1_2_F0_H4_solid')
        CityGMLs['LOD1_2_F0_H5_solid'] = createCityGML('LOD1_2_F0_H5_solid')
        CityGMLs['LOD1_2_F0_H6_solid'] = createCityGML('LOD1_2_F0_H6_solid')
        CityGMLs['LOD1_2_F0_HAvg_solid'] = createCityGML('LOD1_2_F0_HAvg_solid')
        CityGMLs['LOD1_2_F0_HMed_solid'] = createCityGML('LOD1_2_F0_HMed_solid')

    if VARIANTS:
        CityGMLs['LOD1_2_F1_H0_solid'] = createCityGML('LOD1_2_F1_H0_solid')
        CityGMLs['LOD1_2_F1_H1_solid'] = createCityGML('LOD1_2_F1_H1_solid')
        CityGMLs['LOD1_2_F1_H2_solid'] = createCityGML('LOD1_2_F1_H2_solid')
        CityGMLs['LOD1_2_F1_H3_solid'] = createCityGML('LOD1_2_F1_H3_solid')
        CityGMLs['LOD1_2_F1_H4_solid'] = createCityGML('LOD1_2_F1_H4_solid')
        CityGMLs['LOD1_2_F1_H5_solid'] = createCityGML('LOD1_2_F1_H5_solid')
        CityGMLs['LOD1_2_F1_H6_solid'] = createCityGML('LOD1_2_F1_H6_solid')
        CityGMLs['LOD1_2_F1_HAvg_solid'] = createCityGML('LOD1_2_F1_HAvg_solid')
        CityGMLs['LOD1_2_F1_HMed_solid'] = createCityGML('LOD1_2_F1_HMed_solid')

    if VARIANTS:
        CityGMLs['LOD1_2_Fd_H0_solid'] = createCityGML('LOD1_2_Fd_H0_solid')
        CityGMLs['LOD1_2_Fd_H1_solid'] = createCityGML('LOD1_2_Fd_H1_solid')
        CityGMLs['LOD1_2_Fd_H2_solid'] = createCityGML('LOD1_2_Fd_H2_solid')
        CityGMLs['LOD1_2_Fd_H3_solid'] = createCityGML('LOD1_2_Fd_H3_solid')
        CityGMLs['LOD1_2_Fd_H4_solid'] = createCityGML('LOD1_2_Fd_H4_solid')
        CityGMLs['LOD1_2_Fd_H5_solid'] = createCityGML('LOD1_2_Fd_H5_solid')
        CityGMLs['LOD1_2_Fd_H6_solid'] = createCityGML('LOD1_2_Fd_H6_solid')
        CityGMLs['LOD1_2_Fd_HAvg_solid'] = createCityGML('LOD1_2_Fd_HAvg_solid')
        CityGMLs['LOD1_2_Fd_HMed_solid'] = createCityGML('LOD1_2_Fd_HMed_solid')

    if VARIANTS:
        CityGMLs['LOD1_2_F0_H0_semantics'] = createCityGML('LOD1_2_F0_H0_semantics')
        CityGMLs['LOD1_2_F0_H1_semantics'] = createCityGML('LOD1_2_F0_H1_semantics')
        CityGMLs['LOD1_2_F0_H2_semantics'] = createCityGML('LOD1_2_F0_H2_semantics')

    CityGMLs['LOD1_2_F0_H3_semantics'] = createCityGML('LOD1_2_F0_H3_semantics')

    if VARIANTS:
        CityGMLs['LOD1_2_F0_H4_semantics'] = createCityGML('LOD1_2_F0_H4_semantics')
        CityGMLs['LOD1_2_F0_H5_semantics'] = createCityGML('LOD1_2_F0_H5_semantics')
        CityGMLs['LOD1_2_F0_H6_semantics'] = createCityGML('LOD1_2_F0_H6_semantics')
        CityGMLs['LOD1_2_F0_HAvg_semantics'] = createCityGML('LOD1_2_F0_HAvg_semantics')
        CityGMLs['LOD1_2_F0_HMed_semantics'] = createCityGML('LOD1_2_F0_HMed_semantics')

    if VARIANTS:
        CityGMLs['LOD1_2_F1_H0_semantics'] = createCityGML('LOD1_2_F1_H0_semantics')
        CityGMLs['LOD1_2_F1_H1_semantics'] = createCityGML('LOD1_2_F1_H1_semantics')
        CityGMLs['LOD1_2_F1_H2_semantics'] = createCityGML('LOD1_2_F1_H2_semantics')
        CityGMLs['LOD1_2_F1_H3_semantics'] = createCityGML('LOD1_2_F1_H3_semantics')
        CityGMLs['LOD1_2_F1_H4_semantics'] = createCityGML('LOD1_2_F1_H4_semantics')
        CityGMLs['LOD1_2_F1_H5_semantics'] = createCityGML('LOD1_2_F1_H5_semantics')
        CityGMLs['LOD1_2_F1_H6_semantics'] = createCityGML('LOD1_2_F1_H6_semantics')
        CityGMLs['LOD1_2_F1_HAvg_semantics'] = createCityGML('LOD1_2_F1_HAvg_semantics')
        CityGMLs['LOD1_2_F1_HMed_semantics'] = createCityGML('LOD1_2_F1_HMed_semantics')

    if VARIANTS:
        CityGMLs['LOD1_2_Fd_H0_semantics'] = createCityGML('LOD1_2_Fd_H0_semantics')
        CityGMLs['LOD1_2_Fd_H1_semantics'] = createCityGML('LOD1_2_Fd_H1_semantics')
        CityGMLs['LOD1_2_Fd_H2_semantics'] = createCityGML('LOD1_2_Fd_H2_semantics')
        CityGMLs['LOD1_2_Fd_H3_semantics'] = createCityGML('LOD1_2_Fd_H3_semantics')
        CityGMLs['LOD1_2_Fd_H4_semantics'] = createCityGML('LOD1_2_Fd_H4_semantics')
        CityGMLs['LOD1_2_Fd_H5_semantics'] = createCityGML('LOD1_2_Fd_H5_semantics')
        CityGMLs['LOD1_2_Fd_H6_semantics'] = createCityGML('LOD1_2_Fd_H6_semantics')
        CityGMLs['LOD1_2_Fd_HAvg_semantics'] = createCityGML('LOD1_2_Fd_HAvg_semantics')
        CityGMLs['LOD1_2_Fd_HMed_semantics'] = createCityGML('LOD1_2_Fd_HMed_semantics')

#-- LOD1.3
if VARIANTS:
    CityGMLs['LOD1_3_F0_H0'] = createCityGML('LOD1_3_F0_H0')
    CityGMLs['LOD1_3_F0_H1'] = createCityGML('LOD1_3_F0_H1')
    CityGMLs['LOD1_3_F0_H2'] = createCityGML('LOD1_3_F0_H2')

CityGMLs['LOD1_3_F0_H3'] = createCityGML('LOD1_3_F0_H3')

if VARIANTS:
    CityGMLs['LOD1_3_F0_H4'] = createCityGML('LOD1_3_F0_H4')
    CityGMLs['LOD1_3_F0_H5'] = createCityGML('LOD1_3_F0_H5')
    CityGMLs['LOD1_3_F0_H6'] = createCityGML('LOD1_3_F0_H6')
    CityGMLs['LOD1_3_F0_HAvg'] = createCityGML('LOD1_3_F0_HAvg')
    CityGMLs['LOD1_3_F0_HMed'] = createCityGML('LOD1_3_F0_HMed')

if VARIANTS:
    CityGMLs['LOD1_3_F1_H0'] = createCityGML('LOD1_3_F1_H0')
    CityGMLs['LOD1_3_F1_H1'] = createCityGML('LOD1_3_F1_H1')
    CityGMLs['LOD1_3_F1_H2'] = createCityGML('LOD1_3_F1_H2')
    CityGMLs['LOD1_3_F1_H3'] = createCityGML('LOD1_3_F1_H3')
    CityGMLs['LOD1_3_F1_H4'] = createCityGML('LOD1_3_F1_H4')
    CityGMLs['LOD1_3_F1_H5'] = createCityGML('LOD1_3_F1_H5')
    CityGMLs['LOD1_3_F1_H6'] = createCityGML('LOD1_3_F1_H6')
    CityGMLs['LOD1_3_F1_HAvg'] = createCityGML('LOD1_3_F1_HAvg')
    CityGMLs['LOD1_3_F1_HMed'] = createCityGML('LOD1_3_F1_HMed')

if VARIANTS:
    CityGMLs['LOD1_3_Fd_H0'] = createCityGML('LOD1_3_Fd_H0')
    CityGMLs['LOD1_3_Fd_H1'] = createCityGML('LOD1_3_Fd_H1')
    CityGMLs['LOD1_3_Fd_H2'] = createCityGML('LOD1_3_Fd_H2')
    CityGMLs['LOD1_3_Fd_H3'] = createCityGML('LOD1_3_Fd_H3')
    CityGMLs['LOD1_3_Fd_H4'] = createCityGML('LOD1_3_Fd_H4')
    CityGMLs['LOD1_3_Fd_H5'] = createCityGML('LOD1_3_Fd_H5')
    CityGMLs['LOD1_3_Fd_H6'] = createCityGML('LOD1_3_Fd_H6')
    CityGMLs['LOD1_3_Fd_HAvg'] = createCityGML('LOD1_3_Fd_HAvg')
    CityGMLs['LOD1_3_Fd_HMed'] = createCityGML('LOD1_3_Fd_HMed')

if SOLIDS:
    if VARIANTS:
        CityGMLs['LOD1_3_F0_H0_solid'] = createCityGML('LOD1_3_F0_H0_solid')
        CityGMLs['LOD1_3_F0_H1_solid'] = createCityGML('LOD1_3_F0_H1_solid')
        CityGMLs['LOD1_3_F0_H2_solid'] = createCityGML('LOD1_3_F0_H2_solid')

    CityGMLs['LOD1_3_F0_H3_solid'] = createCityGML('LOD1_3_F0_H3_solid')

    if VARIANTS:
        CityGMLs['LOD1_3_F0_H4_solid'] = createCityGML('LOD1_3_F0_H4_solid')
        CityGMLs['LOD1_3_F0_H5_solid'] = createCityGML('LOD1_3_F0_H5_solid')
        CityGMLs['LOD1_3_F0_H6_solid'] = createCityGML('LOD1_3_F0_H6_solid')
        CityGMLs['LOD1_3_F0_HAvg_solid'] = createCityGML('LOD1_3_F0_HAvg_solid')
        CityGMLs['LOD1_3_F0_HMed_solid'] = createCityGML('LOD1_3_F0_HMed_solid')

    if VARIANTS:
        CityGMLs['LOD1_3_F1_H0_solid'] = createCityGML('LOD1_3_F1_H0_solid')
        CityGMLs['LOD1_3_F1_H1_solid'] = createCityGML('LOD1_3_F1_H1_solid')
        CityGMLs['LOD1_3_F1_H2_solid'] = createCityGML('LOD1_3_F1_H2_solid')
        CityGMLs['LOD1_3_F1_H3_solid'] = createCityGML('LOD1_3_F1_H3_solid')
        CityGMLs['LOD1_3_F1_H4_solid'] = createCityGML('LOD1_3_F1_H4_solid')
        CityGMLs['LOD1_3_F1_H5_solid'] = createCityGML('LOD1_3_F1_H5_solid')
        CityGMLs['LOD1_3_F1_H6_solid'] = createCityGML('LOD1_3_F1_H6_solid')
        CityGMLs['LOD1_3_F1_HAvg_solid'] = createCityGML('LOD1_3_F1_HAvg_solid')
        CityGMLs['LOD1_3_F1_HMed_solid'] = createCityGML('LOD1_3_F1_HMed_solid')

    if VARIANTS:
        CityGMLs['LOD1_3_Fd_H0_solid'] = createCityGML('LOD1_3_Fd_H0_solid')
        CityGMLs['LOD1_3_Fd_H1_solid'] = createCityGML('LOD1_3_Fd_H1_solid')
        CityGMLs['LOD1_3_Fd_H2_solid'] = createCityGML('LOD1_3_Fd_H2_solid')
        CityGMLs['LOD1_3_Fd_H3_solid'] = createCityGML('LOD1_3_Fd_H3_solid')
        CityGMLs['LOD1_3_Fd_H4_solid'] = createCityGML('LOD1_3_Fd_H4_solid')
        CityGMLs['LOD1_3_Fd_H5_solid'] = createCityGML('LOD1_3_Fd_H5_solid')
        CityGMLs['LOD1_3_Fd_H6_solid'] = createCityGML('LOD1_3_Fd_H6_solid')
        CityGMLs['LOD1_3_Fd_HAvg_solid'] = createCityGML('LOD1_3_Fd_HAvg_solid')
        CityGMLs['LOD1_3_Fd_HMed_solid'] = createCityGML('LOD1_3_Fd_HMed_solid')

    if VARIANTS:
        CityGMLs['LOD1_3_F0_H0_semantics'] = createCityGML('LOD1_3_F0_H0_semantics')
        CityGMLs['LOD1_3_F0_H1_semantics'] = createCityGML('LOD1_3_F0_H1_semantics')
        CityGMLs['LOD1_3_F0_H2_semantics'] = createCityGML('LOD1_3_F0_H2_semantics')

    CityGMLs['LOD1_3_F0_H3_semantics'] = createCityGML('LOD1_3_F0_H3_semantics')

    if VARIANTS:
        CityGMLs['LOD1_3_F0_H4_semantics'] = createCityGML('LOD1_3_F0_H4_semantics')
        CityGMLs['LOD1_3_F0_H5_semantics'] = createCityGML('LOD1_3_F0_H5_semantics')
        CityGMLs['LOD1_3_F0_H6_semantics'] = createCityGML('LOD1_3_F0_H6_semantics')
        CityGMLs['LOD1_3_F0_HAvg_semantics'] = createCityGML('LOD1_3_F0_HAvg_semantics')
        CityGMLs['LOD1_3_F0_HMed_semantics'] = createCityGML('LOD1_3_F0_HMed_semantics')

    if VARIANTS:
        CityGMLs['LOD1_3_F1_H0_semantics'] = createCityGML('LOD1_3_F1_H0_semantics')
        CityGMLs['LOD1_3_F1_H1_semantics'] = createCityGML('LOD1_3_F1_H1_semantics')
        CityGMLs['LOD1_3_F1_H2_semantics'] = createCityGML('LOD1_3_F1_H2_semantics')
        CityGMLs['LOD1_3_F1_H3_semantics'] = createCityGML('LOD1_3_F1_H3_semantics')
        CityGMLs['LOD1_3_F1_H4_semantics'] = createCityGML('LOD1_3_F1_H4_semantics')
        CityGMLs['LOD1_3_F1_H5_semantics'] = createCityGML('LOD1_3_F1_H5_semantics')
        CityGMLs['LOD1_3_F1_H6_semantics'] = createCityGML('LOD1_3_F1_H6_semantics')
        CityGMLs['LOD1_3_F1_HAvg_semantics'] = createCityGML('LOD1_3_F1_HAvg_semantics')
        CityGMLs['LOD1_3_F1_HMed_semantics'] = createCityGML('LOD1_3_F1_HMed_semantics')

    if VARIANTS:
        CityGMLs['LOD1_3_Fd_H0_semantics'] = createCityGML('LOD1_3_Fd_H0_semantics')
        CityGMLs['LOD1_3_Fd_H1_semantics'] = createCityGML('LOD1_3_Fd_H1_semantics')
        CityGMLs['LOD1_3_Fd_H2_semantics'] = createCityGML('LOD1_3_Fd_H2_semantics')
        CityGMLs['LOD1_3_Fd_H3_semantics'] = createCityGML('LOD1_3_Fd_H3_semantics')
        CityGMLs['LOD1_3_Fd_H4_semantics'] = createCityGML('LOD1_3_Fd_H4_semantics')
        CityGMLs['LOD1_3_Fd_H5_semantics'] = createCityGML('LOD1_3_Fd_H5_semantics')
        CityGMLs['LOD1_3_Fd_H6_semantics'] = createCityGML('LOD1_3_Fd_H6_semantics')
        CityGMLs['LOD1_3_Fd_HAvg_semantics'] = createCityGML('LOD1_3_Fd_HAvg_semantics')
        CityGMLs['LOD1_3_Fd_HMed_semantics'] = createCityGML('LOD1_3_Fd_HMed_semantics')

## LOD2
#-- LOD2.0
CityGMLs['LOD2_0_F0'] = createCityGML('LOD2_0_F0')
if VARIANTS:
    CityGMLs['LOD2_0_Fd'] = createCityGML('LOD2_0_Fd')
    CityGMLs['LOD2_0_F1'] = createCityGML('LOD2_0_F1')
#-- Non semantic version
if SOLIDS:
    CityGMLs['LOD2_0_F0_S0'] = createCityGML('LOD2_0_F0_S0')
if VARIANTS:
    CityGMLs['LOD2_0_Fd_S0'] = createCityGML('LOD2_0_Fd_S0')
    CityGMLs['LOD2_0_F1_S0'] = createCityGML('LOD2_0_F1_S0')
#--Solids
if SOLIDS:
    CityGMLs['LOD2_0_F0_solid'] = createCityGML('LOD2_0_F0_solid')
    if VARIANTS:
        CityGMLs['LOD2_0_Fd_solid'] = createCityGML('LOD2_0_Fd_solid')
        CityGMLs['LOD2_0_F1_solid'] = createCityGML('LOD2_0_F1_solid')

#-- LOD2.1
CityGMLs['LOD2_1_F0'] = createCityGML('LOD2_1_F0')
if VARIANTS:
    CityGMLs['LOD2_1_Fd'] = createCityGML('LOD2_1_Fd')
    CityGMLs['LOD2_1_F1'] = createCityGML('LOD2_1_F1')
#-- Non semantic version
if SOLIDS:
    CityGMLs['LOD2_1_F0_S0'] = createCityGML('LOD2_1_F0_S0')
if VARIANTS:
    CityGMLs['LOD2_1_Fd_S0'] = createCityGML('LOD2_1_Fd_S0')
    CityGMLs['LOD2_1_F1_S0'] = createCityGML('LOD2_1_F1_S0')
#--Solids
if SOLIDS:
    CityGMLs['LOD2_1_F0_solid'] = createCityGML('LOD2_1_F0_solid')
    if VARIANTS:
        CityGMLs['LOD2_1_Fd_solid'] = createCityGML('LOD2_1_Fd_solid')
        CityGMLs['LOD2_1_F1_solid'] = createCityGML('LOD2_1_F1_solid')

#-- LOD2.2
CityGMLs['LOD2_2_F0'] = createCityGML('LOD2_2_F0')
if VARIANTS:
    CityGMLs['LOD2_2_F1'] = createCityGML('LOD2_2_F1')
    CityGMLs['LOD2_2_Fd'] = createCityGML('LOD2_2_Fd')
#-- Non semantic version
if SOLIDS:
    CityGMLs['LOD2_2_F0_S0'] = createCityGML('LOD2_2_F0_S0')
if VARIANTS:
    CityGMLs['LOD2_2_F1_S0'] = createCityGML('LOD2_2_F1_S0')
    CityGMLs['LOD2_2_Fd_S0'] = createCityGML('LOD2_2_Fd_S0')
#--Solids
if SOLIDS:
    CityGMLs['LOD2_2_F0_solid'] = createCityGML('LOD2_2_F0_solid')
    if VARIANTS:
        CityGMLs['LOD2_2_F1_solid'] = createCityGML('LOD2_2_F1_solid')
        CityGMLs['LOD2_2_Fd_solid'] = createCityGML('LOD2_2_Fd_solid')

#-- LOD2.3
CityGMLs['LOD2_3_F0'] = createCityGML('LOD2_3_F0')
if VARIANTS:
    CityGMLs['LOD2_3_Fd'] = createCityGML('LOD2_3_Fd')
#-- Non semantic version
if SOLIDS:
    CityGMLs['LOD2_3_F0_S0'] = createCityGML('LOD2_3_F0_S0')
if VARIANTS:
    CityGMLs['LOD2_3_Fd_S0'] = createCityGML('LOD2_3_Fd_S0')
#--Solids
if SOLIDS:
    CityGMLs['LOD2_3_F0_solid'] = createCityGML('LOD2_3_F0_solid')
    if VARIANTS:
        CityGMLs['LOD2_3_Fd_solid'] = createCityGML('LOD2_3_Fd_solid')

#-- LOD2.3 with dormers
if VARIANTS:
    CityGMLs['LOD2_3_F0_with_dormers'] = createCityGML('LOD2_3_F0_with_dormers')
    CityGMLs['LOD2_3_Fd_with_dormers'] = createCityGML('LOD2_3_Fd_with_dormers')
    #-- Non semantic version
    if SOLIDS:
        CityGMLs['LOD2_3_F0_S0_with_dormers'] = createCityGML('LOD2_3_F0_S0_with_dormers')
    if VARIANTS:
        CityGMLs['LOD2_3_Fd_S0_with_dormers'] = createCityGML('LOD2_3_Fd_S0_with_dormers')
    #--Solids
    if SOLIDS:
        CityGMLs['LOD2_3_F0_solid_with_dormers'] = createCityGML('LOD2_3_F0_solid_with_dormers')
        if VARIANTS:
            CityGMLs['LOD2_3_Fd_solid_with_dormers'] = createCityGML('LOD2_3_Fd_solid_with_dormers')       

#--LOD3 variants
#--Normal LOD3 with flat openings
CityGMLs['LOD3_2'] = createCityGML('LOD3_2')
#--The best LOD3 model available, with embrasures at openings
CityGMLs['LOD3_3'] = createCityGML('LOD3_3')
# #CityGMLs['LOD3BI'] = createCityGML('LOD3BI')
#-- Hybrid models
CityGMLs['LOD3_1'] = createCityGML('LOD3_1')
CityGMLs['LOD3_0'] = createCityGML('LOD3_0')
# CityGMLs['LOD3RF1'] = createCityGML('LOD3RF1')

#-- No semantics
if SOLIDS:
    CityGMLs['LOD3_2_S0'] = createCityGML('LOD3_2_S0')
    CityGMLs['LOD3_3_S0'] = createCityGML('LOD3_3_S0')
    CityGMLs['LOD3_1_S0'] = createCityGML('LOD3_1_S0')
    CityGMLs['LOD3_0_S0'] = createCityGML('LOD3_0_S0')
#--Solid counterparts
if SOLIDS:
    CityGMLs['LOD3_2_solid'] = createCityGML('LOD3_2_solid')
    CityGMLs['LOD3_3_solid'] = createCityGML('LOD3_3_solid')
    CityGMLs['LOD3_1_solid'] = createCityGML('LOD3_1_solid')
    CityGMLs['LOD3_0_solid'] = createCityGML('LOD3_0_solid')

#-- Interior
CityGMLs['interior-LOD0'] = createCityGML('interior-LOD0')
CityGMLs['interior-LOD1'] = createCityGML('interior-LOD1')
CityGMLs['interior-LOD2_2'] = createCityGML('interior-LOD2_2')
CityGMLs['interior-LOD2_3'] = createCityGML('interior-LOD2_3')

#-- Non-building features
if STREETS:
    CityGMLs['Road-LOD0'] = createCityGML('Road-LOD0')
if VEGETATION:
    CityGMLs['PlantCover-LOD0'] = createCityGML('PlantCover-LOD0')
    CityGMLs['PlantCover-LOD1'] = createCityGML('PlantCover-LOD1')

#-- Iterate the list of buildings in the XML and extract their data
buildingcounter = 0
print("Constructing buildings and other city objects...")
if REPORT:
    fish = ProgressFish(total=len(buildings))
for b in buildings:
	#-- Report on the progress
    if REPORT:
        fish.animate(amount=buildingcounter+1)
    buildingcounter += 1
    #-- Building UUID
    ID = b.attrib['ID']
    #-- Origin in (x,y,z) as a list of floats
    origin = b.findall('origin')[0]
    origin_coords = [float(x) for x in origin.text.split(" ")]
    #-- Position in the grid
    order = b.findall('order')[0]
    order = [int(x) for x in order.text.split(" ")]
    #-- Rotation angle
    angle_of_rotationXML = b.findall('rotation')[0]
    angle_of_rotation = float(angle_of_rotationXML.text)
    #-- Dimensions of the building
    xsize = b.findall('xSize')[0]
    xsize = float(xsize.text)
    ysize = b.findall('ySize')[0]
    ysize = float(ysize.text)
    zsize = b.findall('zSize')[0]
    zsize = float(zsize.text)
    #-- Other building geometric properties
    floors = b.findall('floors')[0]
    floors = float(floors.text)
    floorHeight = b.findall('floorHeight')[0]
    floorHeight = float(floorHeight.text)
    embrasure = b.findall('embrasure')[0]
    embrasure = float(embrasure.text)
    wallThickness = b.findall('wallThickness')[0]
    wallThickness = float(wallThickness.text)
    joist = b.findall('joist')[0]
    joist = float(joist.text)

    #-- Store the attributes
    attributes = {}
    attrs = b.findall('properties')[0]
    attributes['yearOfConstruction'] = str(attrs.findall('yearOfConstruction')[0].text)
    attributes['function'] = str(attrs.findall('usage')[0].text)
    attributes['storeysAboveGround'] = str(int(floors))

    #-- Building part
    if BUILDINGPARTS:
        bpartXML = b.findall('buildingPart')
        if len(bpartXML) > 0:
            buildingpart = {}
            bpartXML = bpartXML[0]
            partType = bpartXML.findall('partType')[0].text
            partOrigin = float(bpartXML.findall('partOrigin')[0].text)
            width = float(bpartXML.findall('width')[0].text)
            length = float(bpartXML.findall('length')[0].text)
            height = float(bpartXML.findall('height')[0].text)
            buildingpart['o'] = partOrigin
            buildingpart['type'] = partType
            buildingpart['x'] = width
            buildingpart['y'] = length
            buildingpart['z'] = height
        else:
            buildingpart = None
    else:
        buildingpart = None

    #-- Roof
    roof = b.findall('roof')[0]
    roofType = roof.findall('roofType')[0]
    roofType = roofType.text
    if roofType == 'Flat':
        h = None
        r = None
        ovh = roof.findall('overhangs')[0]
        ovhx = ovh.findall('xlength')[0]
        ovhy = ovh.findall('ylength')[0]
        ovhx = float(ovhx.text)
        ovhy = float(ovhy.text)
    elif roofType == 'Hipped' or roofType == 'Pyramidal':
        h = roof.findall('h')[0]
        h = float(h.text)
        r = roof.findall('r')[0]
        r = float(r.text)
        ovh = roof.findall('overhangs')[0]
        ovhx = ovh.findall('xlength')[0]
        ovhy = ovh.findall('ylength')[0]
        ovhx = float(ovhx.text)
        ovhy = float(ovhy.text)
    else:
        h = roof.findall('h')[0]
        h = float(h.text)
        r = None
        ovh = roof.findall('overhangs')[0]
        ovhx = ovh.findall('xlength')[0]
        ovhy = ovh.findall('ylength')[0]
        ovhx = float(ovhx.text)
        ovhy = float(ovhy.text)

    #-- Overhangs
    if ovh is not None:
        ovh = [ovhx, ovhy]


    #-- Chimney
    chimney = []
    chimneyXML = roof.findall('chimney')
    if len(chimneyXML) > 0:
        chimneyXML = chimneyXML[0]
        chimneyFace = chimneyXML.findall('side')[0]
        chimneyOrigin = chimneyXML.findall('origin')[0]
        chimneyOriginX = chimneyOrigin.findall('x')[0]
        chimneyOriginX = float(chimneyOriginX.text)
        chimneyOriginY = chimneyOrigin.findall('y')[0]
        chimneyOriginY = float(chimneyOriginY.text)
        chimneySize = chimneyXML.findall('size')[0]
        chimneyWidth = chimneySize.findall('width')[0]
        chimneyWidth = float(chimneyWidth.text)
        chimneyHeight = chimneySize.findall('height')[0]
        chimneyHeight = float(chimneyHeight.text)
        chimneyDict = {}
        chimneyDict['side'] = int(chimneyFace.text)
        chimneyDict['origin'] = [chimneyOriginX, chimneyOriginY]
        chimneyDict['size'] = [chimneyWidth, chimneyWidth, chimneyHeight]
        chimney.append(chimneyDict)

    #-- Door
    door = b.findall('door')[0]
    doorFace = door.findall('wall')[0]
    doorOrigin = door.findall('origin')[0]
    doorOriginX = doorOrigin.findall('x')[0]
    doorOriginX = float(doorOriginX.text)
    doorOriginY = doorOrigin.findall('y')[0]
    doorOriginY = float(doorOriginY.text)
    doorSize = door.findall('size')[0]
    doorWidth = doorSize.findall('width')[0]
    doorWidth = float(doorWidth.text)
    doorHeight = doorSize.findall('height')[0]
    doorHeight = float(doorHeight.text)

    doorDict = {}
    doorDict['wall'] = int(doorFace.text)
    doorDict['origin'] = [doorOriginX, doorOriginY]
    doorDict['size'] = [doorWidth, doorHeight]

    #-- Wall windows
    wallWindows = []
    allwindowsXML = b.findall('windows')
    if len(allwindowsXML) > 0:
        allwindowsXML = allwindowsXML[0]
        for winXML in allwindowsXML.findall('window'):
            wallWindows.append({'wall' : int(winXML.findall('wall')[0].text), 'size' : [float((winXML.findall('size')[0]).findall('width')[0].text), float((winXML.findall('size')[0]).findall('height')[0].text)], 'origin' : [float((winXML.findall('origin')[0]).findall('x')[0].text), float((winXML.findall('origin')[0]).findall('y')[0].text)]})
        embrasure = float(winXML.findall('depth')[0].text)
    else:
        embrasure = 0.0

    #-- Dormers
    dormers = []
    alldormersXML = roof.findall('dormers')
    if len(alldormersXML) > 0:
        alldormersXML = alldormersXML[0]
        for dormXML in alldormersXML.findall('dormer'):
            dormers.append({'side' : int(dormXML.findall('side')[0].text), 'size' : [float((dormXML.findall('size')[0]).findall('width')[0].text), float((dormXML.findall('size')[0]).findall('height')[0].text)], 'origin' : [float((dormXML.findall('origin')[0]).findall('x')[0].text), float((dormXML.findall('origin')[0]).findall('y')[0].text)]})


    roofWindows = []
    allrfwinXML = roof.findall('roofWindows')
    if len(allrfwinXML) > 0:
        allrfwinXML = allrfwinXML[0]
        for rfwinXML in allrfwinXML.findall('roofWindow'):
            roofWindows.append({'side' : int(rfwinXML.findall('side')[0].text), 'size' : [float((rfwinXML.findall('size')[0]).findall('width')[0].text), float((rfwinXML.findall('size')[0]).findall('height')[0].text)], 'origin' : [float((rfwinXML.findall('origin')[0]).findall('x')[0].text), float((rfwinXML.findall('origin')[0]).findall('y')[0].text)]})

    #-- Additional data
    additional = {'overhangs' : ovh, 'embrasure': embrasure}

    valueDict = {'ovh' : ovh, 'doorDict' : doorDict, 'wallWindows' : wallWindows, 'dormers' : dormers, 'roofWindows' : roofWindows, 'chimney' : chimney, 'embrasure' : embrasure}

    #-- LOD3, first because we need the output of many parameters like absolute height of the chimney, eaves and corrected overhang lenghts 
    CityGMLs['dummyLOD3'] = createCityGML('dummyLOD3')
    chimneyHeight, eaves, ovhy_recalculated = CityGMLbuildingLOD3Semantics(CityGMLs['dummyLOD3'], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, ovh, r, valueDict['doorDict'], valueDict['wallWindows'], valueDict['dormers'], valueDict['roofWindows'], valueDict['chimney'], valueDict['embrasure'], 1, None, None)
    del CityGMLs['dummyLOD3']

    #-- Adjust for footprint as the roof overhangs projection (modelling rule F1)
    adjorigin = [origin_coords[0]-ovhx, origin_coords[1]-ovhy_recalculated, origin_coords[2]]
    adjxsize = xsize + 2 * ovhx
    adjysize = ysize + 2 * ovhy_recalculated
    adjzsize = zsize - (zsize - eaves)

    #-- Adjust the height of the roof
    if h is not None:
        if roofType == 'Shed':
            adjh = h + 2 * (zsize - eaves)
        else:
            adjh = h + (zsize - eaves)
    else:
        adjh = None

    if r is not None:
        adjr = r + ovhy_recalculated
    else:
        adjr = None

    #-- Adjust for footprint as the offset from the roof overhangs projection (modelling rule Fd)
    offset = 0.2
    #-- Defined here because the coordinates of the roof features have to be adjusted
    
    #-- Edges and other things for the offset
    adjorigin_offset = [origin_coords[0]-ovhx+offset, origin_coords[1]-ovhy_recalculated+offset, origin_coords[2]]
    adjxsize_offset = xsize + 2*(ovhx-offset)
    adjysize_offset = ysize + 2*(ovhy_recalculated-offset)

    #-- Auxiliary data in a dictionary
    aux = {}
    aux['ovhx'] = ovhx
    aux['ovhy'] = ovhy_recalculated
    aux['origin'] = origin_coords
    aux['xsize'] = xsize
    aux['ysize'] = ysize
    aux['zsize'] = zsize
    aux['offset'] = offset
    aux['adjxsize_offset'] = adjxsize_offset
    aux['adjysize_offset'] = adjysize_offset


    if h is not None:
        if offset < ovhx:
            eo = (zsize - eaves) * (ovhx - offset) / ovhx
            adjzsize_offset = zsize - eo
            adjh_offset = h + eo
            if roofType == 'Shed':
                adjh_offset = h + 2*eo
        elif offset == ovhx:
            adjzsize_offset = zsize
            adjh_offset = h
        elif offset > ovhx and ovhx != 0.0:
            eo = (zsize - eaves) * (offset/ovhx) - zsize + eaves
            adjzsize_offset = zsize + eo
            adjh_offset = h - eo
            if roofType == 'Shed':
                adjh_offset = h - 2*eo
        elif ovhx == 0.0:
            eo = h * (offset/(xsize*.5))
            adjzsize_offset = zsize + eo
            adjh_offset = h - eo
            if roofType == 'Shed':
                adjh_offset = h - 2*eo

    else:
        adjzsize_offset = zsize
        adjh_offset = None

    #-- Workaround to calculate the pyramidal and hipped building overhang in y direction
    CityGMLs['dummy'] = createCityGML('dummy')
    dummy1, eaves_offset, ovhy_recalculated_offset = CityGMLbuildingLOD3Semantics(CityGMLs['dummy'], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, adjzsize_offset, adjh_offset, roofType, [offset, offset], r, valueDict['doorDict'], valueDict['wallWindows'], valueDict['dormers'], valueDict['roofWindows'], valueDict['chimney'], valueDict['embrasure'], 1, aux, buildingpart)
    del CityGMLs['dummy']

    if r is not None:
        if r > 0:
            adjr_offset = r + ovhy_recalculated - offset
        else:
            adjr_offset = 0
    else:
        adjr_offset = None


    chimney_ovh = []
    chimney_offset = []
    for chi in chimney:
        chi_ovh = copy.deepcopy(chi)
        chi_offset = copy.deepcopy(chi)
        chi_ovh['origin'] = adjustRoofFeatures(roofType, zsize - eaves, chi['origin'], ovhx, ovhy_recalculated, chi['side'])
        chi_offset['origin'] = adjustRoofFeatures(roofType, zsize - adjzsize_offset, chi['origin'], ovhx - offset, ovhy_recalculated - offset, chi['side'])
        chimney_ovh.append(chi_ovh)
        chimney_offset.append(chi_offset)

    dormers_ovh = []
    dormers_offset = []
    for dor in dormers:
        dor_ovh = copy.deepcopy(dor)
        dor_offset = copy.deepcopy(dor)
        dor_ovh['origin'] = adjustRoofFeatures(roofType, zsize - eaves, dor['origin'], ovhx, ovhy_recalculated, dor['side'])
        dor_offset['origin'] = adjustRoofFeatures(roofType, zsize - adjzsize_offset, dor['origin'], ovhx - offset, ovhy_recalculated - offset, dor['side'])
        dormers_ovh.append(dor_ovh)
        dormers_offset.append(dor_offset)

    roofWindows_ovh = []
    roofWindows_offset = []
    for roofwindow in roofWindows:
        roofwindow_ovh = copy.deepcopy(roofwindow)
        roofwindow_offset = copy.deepcopy(roofwindow)
        roofwindow_ovh['origin'] = adjustRoofFeatures(roofType, zsize - eaves, roofwindow['origin'], ovhx, ovhy_recalculated, roofwindow['side'])
        roofwindow_offset['origin'] = adjustRoofFeatures(roofType, zsize - adjzsize_offset, roofwindow['origin'], ovhx - offset, ovhy_recalculated - offset, roofwindow['side'])
        roofWindows_ovh.append(roofwindow_ovh)
        roofWindows_offset.append(roofwindow_offset)


    #-- Geometric reference for the height
    if adjh is not None:
        onethird = adjh * (1.0/3.0) + adjzsize
        half = adjh * .5 + adjzsize
        twothird = adjh * (2.0/3.0) + adjzsize
    else:
        onethird = adjzsize
        half = adjzsize
        twothird = adjzsize

    ##-- Start generating the CityGML buildings

    #-- Tentative aggregation
    cellsize = 20.0
    if order[0] % 3 == 0 and order[1] % 3 == 0:
        xo = order[0] * cellsize
        yo = order[1] * cellsize
        gxsize = cellsize * 3 - 6.0
        gysize = cellsize * 3 - 6.0
        gen_roofType = 'Flat'
        CityGMLbuildingLOD0(CityGMLs["LOD0_0"], ID, attributes, [xo, yo, 0.0], gxsize, gysize, zsize, h, gen_roofType, None, eaves, '0.0')
        CityGMLbuildingLOD1(CityGMLs["LOD1_0_HMin"], ID, attributes, [xo, yo, 0.0], gxsize, gysize, zsize, h, gen_roofType, None, eaves, '1.0') #-- This one is with the eaves
        if SOLIDS:
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_0_HMin_solid"], ID, attributes, [xo, yo, 0.0], gxsize, gysize, zsize, h, gen_roofType, None, eaves, '1.0') #-- This one is with the eaves
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_0_HMin_semantics"], ID, attributes, [xo, yo, 0.0], gxsize, gysize, zsize, h, gen_roofType, None, eaves, '1.0') #-- This one is with the eaves

    #####-- LOD0
    ##-- LOD0.1
    if VARIANTS:
        CityGMLbuildingLOD0(CityGMLs["LOD0_1_F0_H0"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, eaves, '0.1', aux, buildingpart) #-- This one is with the eaves
        CityGMLbuildingLOD0(CityGMLs["LOD0_1_F0_H1"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, 0.0, None, '0.1', aux, buildingpart)
        CityGMLbuildingLOD0(CityGMLs["LOD0_1_F0_H2"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, onethird, '0.1', aux, buildingpart)
    CityGMLbuildingLOD0(CityGMLs["LOD0_1_F0_H3"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, half, '0.1', aux, buildingpart)
    if VARIANTS:
        CityGMLbuildingLOD0(CityGMLs["LOD0_1_F0_H4"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, twothird, '0.1', aux, buildingpart)
        CityGMLbuildingLOD0(CityGMLs["LOD0_1_F0_H5"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, 1, chimneyHeight, '0.1', aux, buildingpart)
        CityGMLbuildingLOD0(CityGMLs["LOD0_1_F0_H6"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, chimneyHeight, '0.1', aux, buildingpart) #-- This one is with the chimney or eaves

    if VARIANTS:
        CityGMLbuildingLOD0(CityGMLs["LOD0_1_F1_H0"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, eaves, '0.1', aux, buildingpart) #-- This one is with the eaves
        CityGMLbuildingLOD0(CityGMLs["LOD0_1_F1_H1"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, 0.0, None, '0.1', aux, buildingpart)
        CityGMLbuildingLOD0(CityGMLs["LOD0_1_F1_H2"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, onethird, '0.1', aux, buildingpart)
        CityGMLbuildingLOD0(CityGMLs["LOD0_1_F1_H3"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, half, '0.1', aux, buildingpart)
        CityGMLbuildingLOD0(CityGMLs["LOD0_1_F1_H4"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, twothird, '0.1', aux, buildingpart)
        CityGMLbuildingLOD0(CityGMLs["LOD0_1_F1_H5"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, 1, chimneyHeight, '0.1', aux, buildingpart)
        CityGMLbuildingLOD0(CityGMLs["LOD0_1_F1_H6"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, chimneyHeight, '0.1', aux, buildingpart) #-- This one is with the chimney or eaves

    if VARIANTS:
        CityGMLbuildingLOD0(CityGMLs["LOD0_1_Fd_H0"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, eaves, '0.1', aux, buildingpart, True) #-- This one is with the eaves
        CityGMLbuildingLOD0(CityGMLs["LOD0_1_Fd_H1"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, 0.0, None, '0.1', aux, buildingpart, True)
        CityGMLbuildingLOD0(CityGMLs["LOD0_1_Fd_H2"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, onethird, '0.1', aux, buildingpart, True)
        CityGMLbuildingLOD0(CityGMLs["LOD0_1_Fd_H3"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, half, '0.1', aux, buildingpart, True)
        CityGMLbuildingLOD0(CityGMLs["LOD0_1_Fd_H4"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, twothird, '0.1', aux, buildingpart, True)
        CityGMLbuildingLOD0(CityGMLs["LOD0_1_Fd_H5"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, 1, chimneyHeight, '0.1', aux, buildingpart, True)
        CityGMLbuildingLOD0(CityGMLs["LOD0_1_Fd_H6"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, chimneyHeight, '0.1', aux, buildingpart, True) #-- This one is with the chimney or eaves

    ##-- LOD0.2
    if VARIANTS:
        CityGMLbuildingLOD0(CityGMLs["LOD0_2_F0_H0"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, eaves, '0.2', aux, buildingpart) #-- This one is with the eaves
        CityGMLbuildingLOD0(CityGMLs["LOD0_2_F0_H1"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, 0.0, None, '0.2', aux, buildingpart)
        CityGMLbuildingLOD0(CityGMLs["LOD0_2_F0_H2"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, onethird, '0.2', aux, buildingpart)
    CityGMLbuildingLOD0(CityGMLs["LOD0_2_F0_H3"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, half, '0.2', aux, buildingpart)
    if VARIANTS:
        CityGMLbuildingLOD0(CityGMLs["LOD0_2_F0_H4"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, twothird, '0.2', aux, buildingpart)
        CityGMLbuildingLOD0(CityGMLs["LOD0_2_F0_H5"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, 1, chimneyHeight, '0.2', aux, buildingpart)
        CityGMLbuildingLOD0(CityGMLs["LOD0_2_F0_H6"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, chimneyHeight, '0.2', aux, buildingpart) #-- This one is with the chimney or eaves

    if VARIANTS:
        CityGMLbuildingLOD0(CityGMLs["LOD0_2_F1_H0"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, eaves, '0.2', aux, buildingpart) #-- This one is with the eaves
        CityGMLbuildingLOD0(CityGMLs["LOD0_2_F1_H1"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, 0.0, None, '0.2', aux, buildingpart)
        CityGMLbuildingLOD0(CityGMLs["LOD0_2_F1_H2"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, onethird, '0.2', aux, buildingpart)
        CityGMLbuildingLOD0(CityGMLs["LOD0_2_F1_H3"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, half, '0.2', aux, buildingpart)
        CityGMLbuildingLOD0(CityGMLs["LOD0_2_F1_H4"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, twothird, '0.2', aux, buildingpart)
        CityGMLbuildingLOD0(CityGMLs["LOD0_2_F1_H5"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, 1, chimneyHeight, '0.2', aux, buildingpart)
        CityGMLbuildingLOD0(CityGMLs["LOD0_2_F1_H6"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, chimneyHeight, '0.2', aux, buildingpart) #-- This one is with the chimney or eaves

    if VARIANTS:
        CityGMLbuildingLOD0(CityGMLs["LOD0_2_Fd_H0"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, eaves, '0.2', aux, buildingpart, True) #-- This one is with the eaves
        CityGMLbuildingLOD0(CityGMLs["LOD0_2_Fd_H1"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, 0.0, None, '0.2', aux, buildingpart, True)
        CityGMLbuildingLOD0(CityGMLs["LOD0_2_Fd_H2"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, onethird, '0.2', aux, buildingpart, True)
        CityGMLbuildingLOD0(CityGMLs["LOD0_2_Fd_H3"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, half, '0.2', aux, buildingpart, True)
        CityGMLbuildingLOD0(CityGMLs["LOD0_2_Fd_H4"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, twothird, '0.2', aux, buildingpart, True)
        CityGMLbuildingLOD0(CityGMLs["LOD0_2_Fd_H5"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, 1, chimneyHeight, '0.2', aux, buildingpart, True)
        CityGMLbuildingLOD0(CityGMLs["LOD0_2_Fd_H6"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, chimneyHeight, '0.2', aux, buildingpart, True) #-- This one is with the chimney or eaves

    ##-- LOD0.3
    if VARIANTS:
        CityGMLbuildingLOD0(CityGMLs["LOD0_3_F0_H0"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, eaves, '0.3', aux, buildingpart) #-- This one is with the eaves
        CityGMLbuildingLOD0(CityGMLs["LOD0_3_F0_H1"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, 0.0, None, '0.3', aux, buildingpart)
        CityGMLbuildingLOD0(CityGMLs["LOD0_3_F0_H2"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, onethird, '0.3', aux, buildingpart)
    CityGMLbuildingLOD0(CityGMLs["LOD0_3_F0_H3"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, half, '0.3', aux, buildingpart)
    if VARIANTS:
        CityGMLbuildingLOD0(CityGMLs["LOD0_3_F0_H4"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, twothird, '0.3', aux, buildingpart)
        CityGMLbuildingLOD0(CityGMLs["LOD0_3_F0_H5"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, 1, chimneyHeight, '0.3', aux, buildingpart)
        CityGMLbuildingLOD0(CityGMLs["LOD0_3_F0_H6"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, chimneyHeight, '0.3', aux, buildingpart) #-- This one is with the chimney or eaves

    if VARIANTS:
        CityGMLbuildingLOD0(CityGMLs["LOD0_3_F1_H0"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, eaves, '0.3', aux, buildingpart) #-- This one is with the eaves
        CityGMLbuildingLOD0(CityGMLs["LOD0_3_F1_H1"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, 0.0, None, '0.3', aux, buildingpart)
        CityGMLbuildingLOD0(CityGMLs["LOD0_3_F1_H2"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, onethird, '0.3', aux, buildingpart)
        CityGMLbuildingLOD0(CityGMLs["LOD0_3_F1_H3"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, half, '0.3', aux, buildingpart)
        CityGMLbuildingLOD0(CityGMLs["LOD0_3_F1_H4"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, twothird, '0.3', aux, buildingpart)
        CityGMLbuildingLOD0(CityGMLs["LOD0_3_F1_H5"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, 1, chimneyHeight, '0.3', aux, buildingpart)
        CityGMLbuildingLOD0(CityGMLs["LOD0_3_F1_H6"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, chimneyHeight, '0.3', aux, buildingpart) #-- This one is with the chimney or eaves

    if VARIANTS:
        CityGMLbuildingLOD0(CityGMLs["LOD0_3_Fd_H0"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, eaves, '0.3', aux, buildingpart, True) #-- This one is with the eaves
        CityGMLbuildingLOD0(CityGMLs["LOD0_3_Fd_H1"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, 0.0, None, '0.3', aux, buildingpart, True)
        CityGMLbuildingLOD0(CityGMLs["LOD0_3_Fd_H2"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, onethird, '0.3', aux, buildingpart, True)
        CityGMLbuildingLOD0(CityGMLs["LOD0_3_Fd_H3"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, half, '0.3', aux, buildingpart, True)
        CityGMLbuildingLOD0(CityGMLs["LOD0_3_Fd_H4"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, twothird, '0.3', aux, buildingpart, True)
        CityGMLbuildingLOD0(CityGMLs["LOD0_3_Fd_H5"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, 1, chimneyHeight, '0.3', aux, buildingpart, True)
        CityGMLbuildingLOD0(CityGMLs["LOD0_3_Fd_H6"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, chimneyHeight, '0.3', aux, buildingpart, True) #-- This one is with the chimney or eaves


    #####-- LOD1

    ##-- LOD1.3
    #- Multisurface (brep)
    if VARIANTS:
        CityGMLbuildingLOD1(CityGMLs["LOD1_1_F0_H0"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, eaves, '1.1', aux, buildingpart) #-- This one is with the eaves
        CityGMLbuildingLOD1(CityGMLs["LOD1_1_F0_H1"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, 0.0, None, '1.1', aux, buildingpart)
        CityGMLbuildingLOD1(CityGMLs["LOD1_1_F0_H2"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, onethird, '1.1', aux, buildingpart)
    CityGMLbuildingLOD1(CityGMLs["LOD1_1_F0_H3"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, half, '1.1', aux, buildingpart)
    if VARIANTS:
        CityGMLbuildingLOD1(CityGMLs["LOD1_1_F0_H4"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, twothird, '1.1', aux, buildingpart)
        CityGMLbuildingLOD1(CityGMLs["LOD1_1_F0_H5"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, 1, chimneyHeight, '1.1', aux, buildingpart)
        CityGMLbuildingLOD1(CityGMLs["LOD1_1_F0_H6"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, chimneyHeight, '1.1', aux, buildingpart) #-- This one is with the chimney or eaves

    if VARIANTS:
        CityGMLbuildingLOD1(CityGMLs["LOD1_1_F1_H0"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, eaves, '1.1', aux, buildingpart) #-- This one is with the eaves
        CityGMLbuildingLOD1(CityGMLs["LOD1_1_F1_H1"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, 0.0, None, '1.1', aux, buildingpart)
        CityGMLbuildingLOD1(CityGMLs["LOD1_1_F1_H2"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, onethird, '1.1', aux, buildingpart)
        CityGMLbuildingLOD1(CityGMLs["LOD1_1_F1_H3"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, half, '1.1', aux, buildingpart)
        CityGMLbuildingLOD1(CityGMLs["LOD1_1_F1_H4"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, twothird, '1.1', aux, buildingpart)
        CityGMLbuildingLOD1(CityGMLs["LOD1_1_F1_H5"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, 1, chimneyHeight, '1.1', aux, buildingpart)
        CityGMLbuildingLOD1(CityGMLs["LOD1_1_F1_H6"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, chimneyHeight, '1.1', aux, buildingpart) #-- This one is with the chimney or eaves

    if VARIANTS:
        CityGMLbuildingLOD1(CityGMLs["LOD1_1_Fd_H0"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, eaves, '1.1', aux, buildingpart, True) #-- This one is with the eaves
        CityGMLbuildingLOD1(CityGMLs["LOD1_1_Fd_H1"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, 0.0, None, '1.1', aux, buildingpart, True)
        CityGMLbuildingLOD1(CityGMLs["LOD1_1_Fd_H2"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, onethird, '1.1', aux, buildingpart, True)
        CityGMLbuildingLOD1(CityGMLs["LOD1_1_Fd_H3"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, half, '1.1', aux, buildingpart, True)
        CityGMLbuildingLOD1(CityGMLs["LOD1_1_Fd_H4"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, twothird, '1.1', aux, buildingpart, True)
        CityGMLbuildingLOD1(CityGMLs["LOD1_1_Fd_H5"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, 1, chimneyHeight, '1.1', aux, buildingpart, True)
        CityGMLbuildingLOD1(CityGMLs["LOD1_1_Fd_H6"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, chimneyHeight, '1.1', aux, buildingpart, True) #-- This one is with the chimney or eaves
    
    #- Solids
    if SOLIDS:
        if VARIANTS:
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_1_F0_H0_solid"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, eaves, '1.1', aux, buildingpart) #-- This one is with the eaves
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_1_F0_H1_solid"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, 0.0, None, '1.1', aux, buildingpart)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_1_F0_H2_solid"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, onethird, '1.1', aux, buildingpart)
        CityGMLbuildingLOD1Solid(CityGMLs["LOD1_1_F0_H3_solid"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, half, '1.1', aux, buildingpart)
        if VARIANTS:
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_1_F0_H4_solid"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, twothird, '1.1', aux, buildingpart)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_1_F0_H5_solid"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, 1, chimneyHeight, '1.1', aux, buildingpart)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_1_F0_H6_solid"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, chimneyHeight, '1.1', aux, buildingpart) #-- This one is with the chimney or eaves

        if VARIANTS:
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_1_F1_H0_solid"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, eaves, '1.1', aux, buildingpart) #-- This one is with the eaves
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_1_F1_H1_solid"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, 0.0, None, '1.1', aux, buildingpart)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_1_F1_H2_solid"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, onethird, '1.1', aux, buildingpart)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_1_F1_H3_solid"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, half, '1.1', aux, buildingpart)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_1_F1_H4_solid"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, twothird, '1.1', aux, buildingpart)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_1_F1_H5_solid"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, 1, chimneyHeight, '1.1', aux, buildingpart)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_1_F1_H6_solid"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, chimneyHeight, '1.1', aux, buildingpart) #-- This one is with the chimney or eaves

        if VARIANTS:
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_1_Fd_H0_solid"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, eaves, '1.1', aux, buildingpart, True) #-- This one is with the eaves
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_1_Fd_H1_solid"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, 0.0, None, '1.1', aux, buildingpart, True)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_1_Fd_H2_solid"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, onethird, '1.1', aux, buildingpart, True)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_1_Fd_H3_solid"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, half, '1.1', aux, buildingpart, True)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_1_Fd_H4_solid"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, twothird, '1.1', aux, buildingpart, True)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_1_Fd_H5_solid"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, 1, chimneyHeight, '1.1', aux, buildingpart, True)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_1_Fd_H6_solid"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, chimneyHeight, '1.1', aux, buildingpart, True) #-- This one is with the chimney or eaves

        #- Enhanced semantics
        if VARIANTS:
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_1_F0_H0_semantics"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, eaves, '1.1', aux, buildingpart) #-- This one is with the eaves
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_1_F0_H1_semantics"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, 0.0, None, '1.1', aux, buildingpart)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_1_F0_H2_semantics"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, onethird, '1.1', aux, buildingpart)
        CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_1_F0_H3_semantics"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, half, '1.1', aux, buildingpart)
        if VARIANTS:
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_1_F0_H4_semantics"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, twothird, '1.1', aux, buildingpart)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_1_F0_H5_semantics"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, 1, chimneyHeight, '1.1', aux, buildingpart)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_1_F0_H6_semantics"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, chimneyHeight, '1.1', aux, buildingpart) #-- This one is with the chimney or eaves

        if VARIANTS:
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_1_F1_H0_semantics"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, eaves, '1.1', aux, buildingpart) #-- This one is with the eaves
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_1_F1_H1_semantics"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, 0.0, None, '1.1', aux, buildingpart)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_1_F1_H2_semantics"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, onethird, '1.1', aux, buildingpart)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_1_F1_H3_semantics"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, half, '1.1', aux, buildingpart)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_1_F1_H4_semantics"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, twothird, '1.1', aux, buildingpart)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_1_F1_H5_semantics"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, 1, chimneyHeight, '1.1', aux, buildingpart)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_1_F1_H6_semantics"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, chimneyHeight, '1.1', aux, buildingpart) #-- This one is with the chimney or eaves

        if VARIANTS:
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_1_Fd_H0_semantics"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, eaves, '1.1', aux, buildingpart, True) #-- This one is with the eaves
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_1_Fd_H1_semantics"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, 0.0, None, '1.1', aux, buildingpart, True)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_1_Fd_H2_semantics"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, onethird, '1.1', aux, buildingpart, True)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_1_Fd_H3_semantics"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, half, '1.1', aux, buildingpart, True)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_1_Fd_H4_semantics"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, twothird, '1.1', aux, buildingpart, True)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_1_Fd_H5_semantics"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, 1, chimneyHeight, '1.1', aux, buildingpart, True)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_1_Fd_H6_semantics"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, chimneyHeight, '1.1', aux, buildingpart, True) #-- This one is with the chimney or eaves


    ##-- LOD1.2
    #- Multisurface (brep)
    if VARIANTS:
        CityGMLbuildingLOD1(CityGMLs["LOD1_2_F0_H0"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, eaves, '1.2', aux, buildingpart) #-- This one is with the eaves
        CityGMLbuildingLOD1(CityGMLs["LOD1_2_F0_H1"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, 0.0, None, '1.2', aux, buildingpart)
        CityGMLbuildingLOD1(CityGMLs["LOD1_2_F0_H2"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, onethird, '1.2', aux, buildingpart)
    CityGMLbuildingLOD1(CityGMLs["LOD1_2_F0_H3"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, half, '1.2', aux, buildingpart)
    if VARIANTS:
        CityGMLbuildingLOD1(CityGMLs["LOD1_2_F0_H4"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, twothird, '1.2', aux, buildingpart)
        CityGMLbuildingLOD1(CityGMLs["LOD1_2_F0_H5"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, 1, chimneyHeight, '1.2', aux, buildingpart)
        CityGMLbuildingLOD1(CityGMLs["LOD1_2_F0_H6"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, chimneyHeight, '1.2', aux, buildingpart) #-- This one is with the chimney or eaves

    if VARIANTS:
        CityGMLbuildingLOD1(CityGMLs["LOD1_2_F1_H0"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, eaves, '1.2', aux, buildingpart) #-- This one is with the eaves
        CityGMLbuildingLOD1(CityGMLs["LOD1_2_F1_H1"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, 0.0, None, '1.2', aux, buildingpart)
        CityGMLbuildingLOD1(CityGMLs["LOD1_2_F1_H2"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, onethird, '1.2', aux, buildingpart)
        CityGMLbuildingLOD1(CityGMLs["LOD1_2_F1_H3"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, half, '1.2', aux, buildingpart)
        CityGMLbuildingLOD1(CityGMLs["LOD1_2_F1_H4"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, twothird, '1.2', aux, buildingpart)
        CityGMLbuildingLOD1(CityGMLs["LOD1_2_F1_H5"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, 1, chimneyHeight, '1.2', aux, buildingpart)
        CityGMLbuildingLOD1(CityGMLs["LOD1_2_F1_H6"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, chimneyHeight, '1.2', aux, buildingpart) #-- This one is with the chimney or eaves

    if VARIANTS:
        CityGMLbuildingLOD1(CityGMLs["LOD1_2_Fd_H0"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, eaves, '1.2', aux, buildingpart, True) #-- This one is with the eaves
        CityGMLbuildingLOD1(CityGMLs["LOD1_2_Fd_H1"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, 0.0, None, '1.2', aux, buildingpart, True)
        CityGMLbuildingLOD1(CityGMLs["LOD1_2_Fd_H2"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, onethird, '1.2', aux, buildingpart, True)
        CityGMLbuildingLOD1(CityGMLs["LOD1_2_Fd_H3"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, half, '1.2', aux, buildingpart, True)
        CityGMLbuildingLOD1(CityGMLs["LOD1_2_Fd_H4"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, twothird, '1.2', aux, buildingpart, True)
        CityGMLbuildingLOD1(CityGMLs["LOD1_2_Fd_H5"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, 1, chimneyHeight, '1.2', aux, buildingpart, True)
        CityGMLbuildingLOD1(CityGMLs["LOD1_2_Fd_H6"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, chimneyHeight, '1.2', aux, buildingpart, True) #-- This one is with the chimney or eaves

    #- Solids
    if SOLIDS:
        if VARIANTS:
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_2_F0_H0_solid"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, eaves, '1.2', aux, buildingpart) #-- This one is with the eaves
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_2_F0_H1_solid"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, 0.0, None, '1.2', aux, buildingpart)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_2_F0_H2_solid"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, onethird, '1.2', aux, buildingpart)
        CityGMLbuildingLOD1Solid(CityGMLs["LOD1_2_F0_H3_solid"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, half, '1.2', aux, buildingpart)
        if VARIANTS:
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_2_F0_H4_solid"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, twothird, '1.2', aux, buildingpart)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_2_F0_H5_solid"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, 1, chimneyHeight, '1.2', aux, buildingpart)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_2_F0_H6_solid"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, chimneyHeight, '1.2', aux, buildingpart) #-- This one is with the chimney or eaves

        if VARIANTS:
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_2_F1_H0_solid"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, eaves, '1.2', aux, buildingpart) #-- This one is with the eaves
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_2_F1_H1_solid"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, 0.0, None, '1.2', aux, buildingpart)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_2_F1_H2_solid"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, onethird, '1.2', aux, buildingpart)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_2_F1_H3_solid"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, half, '1.2', aux, buildingpart)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_2_F1_H4_solid"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, twothird, '1.2', aux, buildingpart)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_2_F1_H5_solid"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, 1, chimneyHeight, '1.2', aux, buildingpart)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_2_F1_H6_solid"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, chimneyHeight, '1.2', aux, buildingpart) #-- This one is with the chimney or eaves

        if VARIANTS:
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_2_Fd_H0_solid"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, eaves, '1.2', aux, buildingpart, True) #-- This one is with the eaves
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_2_Fd_H1_solid"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, 0.0, None, '1.2', aux, buildingpart, True)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_2_Fd_H2_solid"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, onethird, '1.2', aux, buildingpart, True)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_2_Fd_H3_solid"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, half, '1.2', aux, buildingpart, True)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_2_Fd_H4_solid"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, twothird, '1.2', aux, buildingpart, True)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_2_Fd_H5_solid"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, 1, chimneyHeight, '1.2', aux, buildingpart, True)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_2_Fd_H6_solid"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, chimneyHeight, '1.2', aux, buildingpart, True) #-- This one is with the chimney or eaves


        #- Semantics
        if VARIANTS:
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_2_F0_H0_semantics"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, eaves, '1.2', aux, buildingpart) #-- This one is with the eaves
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_2_F0_H1_semantics"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, 0.0, None, '1.2', aux, buildingpart)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_2_F0_H2_semantics"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, onethird, '1.2', aux, buildingpart)
        CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_2_F0_H3_semantics"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, half, '1.2', aux, buildingpart)
        if VARIANTS:
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_2_F0_H4_semantics"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, twothird, '1.2', aux, buildingpart)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_2_F0_H5_semantics"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, 1, chimneyHeight, '1.2', aux, buildingpart)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_2_F0_H6_semantics"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, chimneyHeight, '1.2', aux, buildingpart) #-- This one is with the chimney or eaves

        if VARIANTS:
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_2_F1_H0_semantics"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, eaves, '1.2', aux, buildingpart) #-- This one is with the eaves
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_2_F1_H1_semantics"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, 0.0, None, '1.2', aux, buildingpart)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_2_F1_H2_semantics"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, onethird, '1.2', aux, buildingpart)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_2_F1_H3_semantics"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, half, '1.2', aux, buildingpart)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_2_F1_H4_semantics"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, twothird, '1.2', aux, buildingpart)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_2_F1_H5_semantics"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, 1, chimneyHeight, '1.2', aux, buildingpart)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_2_F1_H6_semantics"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, chimneyHeight, '1.2', aux, buildingpart) #-- This one is with the chimney or eaves

        if VARIANTS:
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_2_Fd_H0_semantics"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, eaves, '1.2', aux, buildingpart, True) #-- This one is with the eaves
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_2_Fd_H1_semantics"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, 0.0, None, '1.2', aux, buildingpart, True)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_2_Fd_H2_semantics"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, onethird, '1.2', aux, buildingpart, True)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_2_Fd_H3_semantics"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, half, '1.2', aux, buildingpart, True)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_2_Fd_H4_semantics"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, twothird, '1.2', aux, buildingpart, True)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_2_Fd_H5_semantics"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, 1, chimneyHeight, '1.2', aux, buildingpart, True)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_2_Fd_H6_semantics"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, chimneyHeight, '1.2', aux, buildingpart, True) #-- This one is with the chimney or eaves


    ##-- LOD1.3
    #- Multisurface (brep)
    if VARIANTS:
        CityGMLbuildingLOD1(CityGMLs["LOD1_3_F0_H0"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, eaves, '1.3', aux, buildingpart) #-- This one is with the eaves
        CityGMLbuildingLOD1(CityGMLs["LOD1_3_F0_H1"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, 0.0, None, '1.3', aux, buildingpart)
        CityGMLbuildingLOD1(CityGMLs["LOD1_3_F0_H2"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, onethird, '1.3', aux, buildingpart)
    CityGMLbuildingLOD1(CityGMLs["LOD1_3_F0_H3"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, half, '1.3', aux, buildingpart)
    if VARIANTS:
        CityGMLbuildingLOD1(CityGMLs["LOD1_3_F0_H4"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, twothird, '1.3', aux, buildingpart)
        CityGMLbuildingLOD1(CityGMLs["LOD1_3_F0_H5"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, 1, chimneyHeight, '1.3', aux, buildingpart)
        CityGMLbuildingLOD1(CityGMLs["LOD1_3_F0_H6"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, chimneyHeight, '1.3', aux, buildingpart) #-- This one is with the chimney or eaves

    if VARIANTS:
        CityGMLbuildingLOD1(CityGMLs["LOD1_3_F1_H0"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, eaves, '1.3', aux, buildingpart) #-- This one is with the eaves
        CityGMLbuildingLOD1(CityGMLs["LOD1_3_F1_H1"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, 0.0, None, '1.3', aux, buildingpart)
        CityGMLbuildingLOD1(CityGMLs["LOD1_3_F1_H2"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, onethird, '1.3', aux, buildingpart)
        CityGMLbuildingLOD1(CityGMLs["LOD1_3_F1_H3"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, half, '1.3', aux, buildingpart)
        CityGMLbuildingLOD1(CityGMLs["LOD1_3_F1_H4"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, twothird, '1.3', aux, buildingpart)
        CityGMLbuildingLOD1(CityGMLs["LOD1_3_F1_H5"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, 1, chimneyHeight, '1.3', aux, buildingpart)
        CityGMLbuildingLOD1(CityGMLs["LOD1_3_F1_H6"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, chimneyHeight, '1.3', aux, buildingpart) #-- This one is with the chimney or eaves

    if VARIANTS:
        CityGMLbuildingLOD1(CityGMLs["LOD1_3_Fd_H0"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, eaves, '1.3', aux, buildingpart, True) #-- This one is with the eaves
        CityGMLbuildingLOD1(CityGMLs["LOD1_3_Fd_H1"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, 0.0, None, '1.3', aux, buildingpart, True)
        CityGMLbuildingLOD1(CityGMLs["LOD1_3_Fd_H2"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, onethird, '1.3', aux, buildingpart, True)
        CityGMLbuildingLOD1(CityGMLs["LOD1_3_Fd_H3"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, half, '1.3', aux, buildingpart, True)
        CityGMLbuildingLOD1(CityGMLs["LOD1_3_Fd_H4"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, twothird, '1.3', aux, buildingpart, True)
        CityGMLbuildingLOD1(CityGMLs["LOD1_3_Fd_H5"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, 1, chimneyHeight, '1.3', aux, buildingpart, True)
        CityGMLbuildingLOD1(CityGMLs["LOD1_3_Fd_H6"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, chimneyHeight, '1.3', aux, buildingpart, True) #-- This one is with the chimney or eaves

    #- Solids
    if SOLIDS:
        if VARIANTS:
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_3_F0_H0_solid"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, eaves, '1.3', aux, buildingpart) #-- This one is with the eaves
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_3_F0_H1_solid"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, 0.0, None, '1.3', aux, buildingpart)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_3_F0_H2_solid"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, onethird, '1.3', aux, buildingpart)
        CityGMLbuildingLOD1Solid(CityGMLs["LOD1_3_F0_H3_solid"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, half, '1.3', aux, buildingpart)
        if VARIANTS:
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_3_F0_H4_solid"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, twothird, '1.3', aux, buildingpart)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_3_F0_H5_solid"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, 1, chimneyHeight, '1.3', aux, buildingpart)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_3_F0_H6_solid"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, chimneyHeight, '1.3', aux, buildingpart) #-- This one is with the chimney or eaves

        if VARIANTS:
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_3_F1_H0_solid"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, eaves, '1.3', aux, buildingpart) #-- This one is with the eaves
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_3_F1_H1_solid"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, 0.0, None, '1.3', aux, buildingpart)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_3_F1_H2_solid"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, onethird, '1.3', aux, buildingpart)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_3_F1_H3_solid"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, half, '1.3', aux, buildingpart)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_3_F1_H4_solid"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, twothird, '1.3', aux, buildingpart)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_3_F1_H5_solid"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, 1, chimneyHeight, '1.3', aux, buildingpart)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_3_F1_H6_solid"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, chimneyHeight, '1.3', aux, buildingpart) #-- This one is with the chimney or eaves

        if VARIANTS:
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_3_Fd_H0_solid"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, eaves, '1.3', aux, buildingpart, True) #-- This one is with the eaves
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_3_Fd_H1_solid"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, 0.0, None, '1.3', aux, buildingpart, True)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_3_Fd_H2_solid"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, onethird, '1.3', aux, buildingpart, True)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_3_Fd_H3_solid"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, half, '1.3', aux, buildingpart, True)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_3_Fd_H4_solid"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, twothird, '1.3', aux, buildingpart, True)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_3_Fd_H5_solid"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, 1, chimneyHeight, '1.3', aux, buildingpart, True)
            CityGMLbuildingLOD1Solid(CityGMLs["LOD1_3_Fd_H6_solid"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, chimneyHeight, '1.3', aux, buildingpart, True) #-- This one is with the chimney or eaves

        #- Semantics
        if VARIANTS:
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_3_F0_H0_semantics"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, eaves, '1.3', aux, buildingpart) #-- This one is with the eaves
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_3_F0_H1_semantics"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, 0.0, None, '1.3', aux, buildingpart)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_3_F0_H2_semantics"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, onethird, '1.3', aux, buildingpart)
        CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_3_F0_H3_semantics"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, half, '1.3', aux, buildingpart)
        if VARIANTS:
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_3_F0_H4_semantics"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, twothird, '1.3', aux, buildingpart)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_3_F0_H5_semantics"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, 1, chimneyHeight, '1.3', aux, buildingpart)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_3_F0_H6_semantics"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, None, chimneyHeight, '1.3', aux, buildingpart) #-- This one is with the chimney or eaves

        if VARIANTS:
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_3_F1_H0_semantics"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, eaves, '1.3', aux, buildingpart) #-- This one is with the eaves
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_3_F1_H1_semantics"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, 0.0, None, '1.3', aux, buildingpart)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_3_F1_H2_semantics"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, onethird, '1.3', aux, buildingpart)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_3_F1_H3_semantics"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, half, '1.3', aux, buildingpart)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_3_F1_H4_semantics"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, twothird, '1.3', aux, buildingpart)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_3_F1_H5_semantics"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, 1, chimneyHeight, '1.3', aux, buildingpart)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_3_F1_H6_semantics"], ID, attributes, adjorigin, adjxsize, adjysize, zsize, h, roofType, None, chimneyHeight, '1.3', aux, buildingpart) #-- This one is with the chimney or eaves

        if VARIANTS:
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_3_Fd_H0_semantics"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, eaves, '1.3', aux, buildingpart, True) #-- This one is with the eaves
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_3_Fd_H1_semantics"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, 0.0, None, '1.3', aux, buildingpart, True)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_3_Fd_H2_semantics"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, onethird, '1.3', aux, buildingpart, True)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_3_Fd_H3_semantics"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, half, '1.3', aux, buildingpart, True)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_3_Fd_H4_semantics"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, twothird, '1.3', aux, buildingpart, True)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_3_Fd_H5_semantics"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, 1, chimneyHeight, '1.3', aux, buildingpart, True)
            CityGMLbuildingLOD1Semantics(CityGMLs["LOD1_3_Fd_H6_semantics"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, zsize, h, roofType, None, chimneyHeight, '1.3', aux, buildingpart, True) #-- This one is with the chimney or eaves


    #--LOD2
    #-LOD2.0
    CityGMLbuildingLOD2Semantics(CityGMLs["LOD2_0_F0"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, r, None, '2.0', aux, buildingpart)
    if VARIANTS:
        CityGMLbuildingLOD2Semantics(CityGMLs["LOD2_0_F1"], ID, attributes, adjorigin, adjxsize, adjysize, adjzsize, adjh, roofType, adjr, None, '2.0', aux, buildingpart)
        CityGMLbuildingLOD2Semantics(CityGMLs["LOD2_0_Fd"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, adjzsize_offset, adjh_offset, roofType, adjr_offset, None, '2.0', aux, buildingpart, True)
    if SOLIDS:
        CityGMLbuildingLOD2Solid(CityGMLs["LOD2_0_F0_S0"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, r, None, 'brep', '2.0', aux, buildingpart)
    if SOLIDS:
        if VARIANTS:
            CityGMLbuildingLOD2Solid(CityGMLs["LOD2_0_F1_S0"], ID, attributes, adjorigin, adjxsize, adjysize, adjzsize, adjh, roofType, adjr, None, 'brep', '2.0', aux, buildingpart)
            CityGMLbuildingLOD2Solid(CityGMLs["LOD2_0_Fd_S0"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, adjzsize_offset, adjh_offset, roofType, adjr_offset, None, 'brep', '2.0', aux, buildingpart, True)
        CityGMLbuildingLOD2Solid(CityGMLs["LOD2_0_F0_solid"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, r, None, 'solid', '2.0', aux, buildingpart)
        if VARIANTS:
            CityGMLbuildingLOD2Solid(CityGMLs["LOD2_0_F1_solid"], ID, attributes, adjorigin, adjxsize, adjysize, adjzsize, adjh, roofType, adjr, None, 'solid', '2.0', aux, buildingpart)
            CityGMLbuildingLOD2Solid(CityGMLs["LOD2_0_Fd_solid"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, adjzsize_offset, adjh_offset, roofType, adjr_offset, None, 'solid', '2.0', aux, buildingpart, True)

    #-LOD2.1
    CityGMLbuildingLOD2Semantics(CityGMLs["LOD2_1_F0"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, r, None, '2.1', aux, buildingpart)
    if VARIANTS:
        CityGMLbuildingLOD2Semantics(CityGMLs["LOD2_1_F1"], ID, attributes, adjorigin, adjxsize, adjysize, adjzsize, adjh, roofType, adjr, None, '2.1', aux, buildingpart)
        CityGMLbuildingLOD2Semantics(CityGMLs["LOD2_1_Fd"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, adjzsize_offset, adjh_offset, roofType, adjr_offset, None, '2.1', aux, buildingpart, True)
    if SOLIDS: 
        CityGMLbuildingLOD2Solid(CityGMLs["LOD2_1_F0_S0"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, r, None, 'brep', '2.1', aux, buildingpart)
        if VARIANTS:
            CityGMLbuildingLOD2Solid(CityGMLs["LOD2_1_F1_S0"], ID, attributes, adjorigin, adjxsize, adjysize, adjzsize, adjh, roofType, adjr, None, 'brep', '2.1', aux, buildingpart)
            CityGMLbuildingLOD2Solid(CityGMLs["LOD2_1_Fd_S0"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, adjzsize_offset, adjh_offset, roofType, adjr_offset, None, 'brep', '2.1', aux, buildingpart, True)   
        CityGMLbuildingLOD2Solid(CityGMLs["LOD2_1_F0_solid"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, r, None, 'solid', '2.1', aux, buildingpart)
        if VARIANTS:
            CityGMLbuildingLOD2Solid(CityGMLs["LOD2_1_F1_solid"], ID, attributes, adjorigin, adjxsize, adjysize, adjzsize, adjh, roofType, adjr, None, 'solid', '2.1', aux, buildingpart)
            CityGMLbuildingLOD2Solid(CityGMLs["LOD2_1_Fd_solid"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, adjzsize_offset, adjh_offset, roofType, adjr_offset, None, 'solid', '2.1', aux, buildingpart, True)


    #-LOD2.2
    #-Realised with LOD3 functions for programming reasons
    CityGMLbuildingLOD3Semantics(CityGMLs['LOD2_2_F0'], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, [0.0, 0.0], r, None, None, dormers, None, None, None, 1, aux, buildingpart, True)
    if SOLIDS:
        CityGMLbuildingLOD3Solid(CityGMLs['LOD2_2_F0_solid'], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, [0.0, 0.0], r, None, None, dormers, None, None, None, additional, 'solid', aux, buildingpart)
        CityGMLbuildingLOD3Solid(CityGMLs['LOD2_2_F0_S0'], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, [0.0, 0.0], r, None, None, dormers, None, None, None, additional, 'brep', aux, buildingpart)
    if VARIANTS:
        CityGMLbuildingLOD3Semantics(CityGMLs['LOD2_2_F1'], ID, attributes, adjorigin, adjxsize, adjysize, adjzsize, adjh, roofType, [0.0, 0.0], adjr, None, None, dormers_ovh, None, None, None, 1, aux, buildingpart, True)
        CityGMLbuildingLOD3Semantics(CityGMLs['LOD2_2_Fd'], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, adjzsize_offset, adjh_offset, roofType, [offset, offset], adjr_offset, None, None, dormers_offset, None, None, None, 1, aux, buildingpart, True)
        if SOLIDS:
            CityGMLbuildingLOD3Solid(CityGMLs['LOD2_2_F1_solid'], ID, attributes, adjorigin, adjxsize, adjysize, adjzsize, adjh, roofType, [0.0, 0.0], adjr, None, None, dormers_ovh, None, None, None, additional, 'solid', aux, buildingpart)
            CityGMLbuildingLOD3Solid(CityGMLs['LOD2_2_F1_S0'], ID, attributes, adjorigin, adjxsize, adjysize, adjzsize, adjh, roofType, [0.0, 0.0], adjr, None, None, dormers_ovh, None, None, None, additional, 'brep', aux, buildingpart)
            CityGMLbuildingLOD3Solid(CityGMLs['LOD2_2_Fd_solid'], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, adjzsize_offset, adjh_offset, roofType, [offset, offset], adjr_offset, None, None, dormers_offset, None, None, None, additional, 'solid', aux, buildingpart)
            CityGMLbuildingLOD3Solid(CityGMLs['LOD2_2_Fd_S0'], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, adjzsize_offset, adjh_offset, roofType, [offset, offset], adjr_offset, None, None, dormers_offset, None, None, None, additional, 'brep', aux, buildingpart)

    #-LOD2.3
    CityGMLbuildingLOD2Semantics(CityGMLs["LOD2_3_F0"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, r, ovh, '2.3', aux, buildingpart)

    if VARIANTS:
        CityGMLbuildingLOD2Semantics(CityGMLs["LOD2_3_Fd"], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, adjzsize_offset, adjh_offset, roofType, adjr_offset, [offset, offset], '2.3', aux, buildingpart, True)
        if SOLIDS:
            CityGMLbuildingLOD3Solid(CityGMLs['LOD2_3_F0_S0'], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, ovh, r, None, None, None, None, None, None, additional, 'brep', aux, buildingpart)
        if VARIANTS and SOLIDS:
            CityGMLbuildingLOD3Solid(CityGMLs['LOD2_3_Fd_S0'], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, adjzsize_offset, adjh_offset, roofType, [offset, offset], adjr_offset, None, None, None, None, None, None, additional, 'brep', aux, buildingpart)
        if SOLIDS:
            CityGMLbuildingLOD3Solid(CityGMLs["LOD2_3_F0_solid"], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, [0.0, 0.0], r, None, None, None, None, None, None, additional, 'solid', aux, buildingpart)
        if VARIANTS and SOLIDS:
            CityGMLbuildingLOD3Solid(CityGMLs['LOD2_3_Fd_solid'], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, adjzsize_offset, adjh_offset, roofType, [offset, offset], adjr_offset, None, None, None, None, None, None, additional, 'solid', aux, buildingpart)

    #-LOD2.3 with dormers
    #-Realised with LOD3 functions for programming reasons
    if VARIANTS:
        CityGMLbuildingLOD3Semantics(CityGMLs['LOD2_3_F0_with_dormers'], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, ovh, r, None, None, dormers, None, None, None, 1, aux, buildingpart, True)
        if SOLIDS:
            CityGMLbuildingLOD3Solid(CityGMLs['LOD2_3_F0_solid_with_dormers'], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, ovh, r, None, None, dormers, None, None, None, additional, 'solid', aux, buildingpart)
            CityGMLbuildingLOD3Solid(CityGMLs['LOD2_3_F0_S0_with_dormers'], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, ovh, r, None, None, dormers, None, None, None, additional, 'brep', aux, buildingpart)
        CityGMLbuildingLOD3Semantics(CityGMLs['LOD2_3_Fd_with_dormers'], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, adjzsize_offset, adjh_offset, roofType, [offset, offset], adjr_offset, None, None, dormers_offset, None, None, None, 1, aux, buildingpart, True)
        if SOLIDS:
            CityGMLbuildingLOD3Solid(CityGMLs['LOD2_3_Fd_solid_with_dormers'], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, adjzsize_offset, adjh_offset, roofType, [offset, offset], adjr_offset, None, None, dormers_offset, None, None, None, additional, 'solid', aux, buildingpart)
            CityGMLbuildingLOD3Solid(CityGMLs['LOD2_3_Fd_S0_with_dormers'], ID, attributes, adjorigin_offset, adjxsize_offset, adjysize_offset, adjzsize_offset, adjh_offset, roofType, [offset, offset], adjr_offset, None, None, dormers_offset, None, None, None, additional, 'brep', aux, buildingpart)



    #-- LOD3 variants
    #-- LOD3.0
    CityGMLbuildingLOD3Semantics(CityGMLs['LOD3_2'], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, ovh, r, doorDict, wallWindows, dormers, roofWindows, chimney, None, 1, aux, buildingpart)
    if SOLIDS:
        CityGMLbuildingLOD3Solid(CityGMLs['LOD3_2_solid'], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, ovh, r, None, None, dormers, None, None, None, additional, 'solid', aux, buildingpart)
        CityGMLbuildingLOD3Solid(CityGMLs['LOD3_2_S0'], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, ovh, r, None, None, dormers, None, None, None, additional, 'brep', aux, buildingpart)
    #-- LOD3.1
    CityGMLbuildingLOD3Semantics(CityGMLs['LOD3_3'], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, ovh, r, doorDict, wallWindows, dormers, roofWindows, chimney, embrasure, 1, aux, buildingpart)
    if SOLIDS:
        CityGMLbuildingLOD3Solid(CityGMLs['LOD3_3_solid'], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, ovh, r, doorDict, wallWindows, dormers, roofWindows, chimney, embrasure, 1, 'solid', aux, buildingpart)
        CityGMLbuildingLOD3Solid(CityGMLs['LOD3_3_S0'], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, ovh, r, doorDict, wallWindows, dormers, roofWindows, chimney, embrasure, 1, 'brep', aux, buildingpart)
    #-- Hybrid models
    CityGMLbuildingLOD3Semantics(CityGMLs['LOD3_1'], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, ovh, r, doorDict, wallWindows, None, None, None, None, 1, aux, buildingpart)
    CityGMLbuildingLOD3Semantics(CityGMLs['LOD3_0'], ID, attributes, adjorigin, adjxsize, adjysize, adjzsize, adjh, roofType, [0.0, 0.0], adjr, None, None, dormers_ovh, roofWindows_ovh, chimney_ovh, None, 1, aux, buildingpart, True)
    if SOLIDS:
        CityGMLbuildingLOD3Solid(CityGMLs['LOD3_1_solid'], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, ovh, r, doorDict, wallWindows, None, None, None, None, 1, 'solid', aux, buildingpart)
        CityGMLbuildingLOD3Solid(CityGMLs['LOD3_0_solid'], ID, attributes, adjorigin, adjxsize, adjysize, adjzsize, adjh, roofType, [0.0, 0.0], adjr, None, None, dormers_ovh, roofWindows_ovh, chimney_ovh, None, 1, 'solid', aux, buildingpart, True)
        CityGMLbuildingLOD3Solid(CityGMLs['LOD3_1_S0'], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, ovh, r, doorDict, wallWindows, None, None, None, None, 1, 'brep', aux, buildingpart)
        CityGMLbuildingLOD3Solid(CityGMLs['LOD3_0_S0'], ID, attributes, adjorigin, adjxsize, adjysize, adjzsize, adjh, roofType, [0.0, 0.0], adjr, None, None, dormers_ovh, roofWindows_ovh, chimney_ovh, None, 1, 'brep', aux, buildingpart, True)
    # #-- BI without structured semantics
    # CityGMLbuildingLOD3Semantics(CityGMLs['LOD3BI'], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, ovh, r, doorDict, wallWindows, dormers, roofWindows, chimney, embrasure, 0)
    # CityGMLbuildingLOD3Semantics(CityGMLs['LOD3RF1'], ID, attributes, adjorigin, adjxsize, adjysize, adjzsize, adjh, roofType, [0.0, 0.0], adjr, None, None, dormers, roofWindows, chimney, embrasure, additional)
    # #CityGMLbuildingLOD3Solid(CityGMLs['LOD3-solid'], ID, attributes, origin_coords, xsize, ysize, zsize, h, roofType, ovh, r, None, None, dormers, None, None, None, additional)

    #-- Interior
    CityGMLbuildingInteriorLOD0(CityGMLs['interior-LOD0'], ID, attributes, origin_coords, xsize, ysize, zsize, h, floors, floorHeight, roofType, r, wallThickness, joist, aux, buildingpart)
    CityGMLbuildingInteriorLOD1(CityGMLs['interior-LOD1'], ID, attributes, origin_coords, xsize, ysize, zsize, h, floors, floorHeight, roofType, r, wallThickness, joist, aux, buildingpart)
    CityGMLbuildingInteriorLOD2(CityGMLs['interior-LOD2_2'], ID, attributes, origin_coords, xsize, ysize, zsize, h, floors, floorHeight, roofType, r, wallThickness, joist, aux, buildingpart)
    CityGMLbuildingInteriorLOD2(CityGMLs['interior-LOD2_3'], ID, attributes, origin_coords, xsize, ysize, zsize, h, floors, floorHeight, roofType, r, wallThickness, joist, aux, buildingpart, dormers)

    #-- Perform the rotation of coordinates
    if ROTATIONENABLED:
        radian_rotation = math.radians(angle_of_rotation)
        sine_rotation = math.sin(radian_rotation)
        cosine_rotation = math.cos(radian_rotation)
        for representation in CityGMLs:
            for entity in CityGMLs[representation]:
                #-- Iterate cityObjectMembers
                if entity.tag == "cityObjectMember":
                    #-- Select the current one
                    if entity.getchildren()[0].attrib['{%s}id' % ns_gml] == ID:
                        #-- Get the building XML node
                        curr_b_inxml = entity.getchildren()[0]
                        #-- Store all the <gml:posList> in a list
                        posList_to_rotate = curr_b_inxml.findall(".//{%s}posList" % ns_gml)
                        for pos in posList_to_rotate:
                            points_to_rotate = GMLstring2points(pos.text)
                            new_rotated_points = ''
                            for point_to_rotate in points_to_rotate:
                                rotated_point = rotator(point_to_rotate, sine_rotation, cosine_rotation, origin_coords)
                                new_rotated_points += GMLPointList(rotated_point) + ' '
                            pos.text = new_rotated_points[:-1]

#-- End of loop of each building

if STREETS:
    for s in streets:
        street_outline = s.findall('outline')[0]
        street_outline_coors = [float(x) for x in street_outline.text.split(" ")]
        street_holes_collection = s.findall('holes')[0]
        street_holes = street_holes_collection.findall('hole')
        street_data = [street_outline_coors, []]
        for street_hole in street_holes:
            street_hole_coors = [float(x) for x in street_hole.text.split(" ")]
            street_data[1].append(street_hole_coors)        
        CityGMLstreets(CityGMLs['Road-LOD0'], street_data)

if VEGETATION:
    for pccollection in plantcover:
        pcs = pccollection.findall('park')
        for pc in pcs:
            park_outline = pc.findall('outline')[0]
            park_outline_coors = [float(x) for x in park_outline.text.split(" ")]
            park_height = pc.findall('height')[0].text
            pc_data = [park_outline_coors, park_height]
            CityGMLplantCoverLOD0(CityGMLs['PlantCover-LOD0'], pc_data)
            CityGMLplantCoverLOD1(CityGMLs['PlantCover-LOD1'], pc_data)

#-- Write to file(s)
print("\nGenerated", len(CityGMLs), "CityGML file(s) in the memory. Now writing to disk...")
filecounter = 0
if REPORT:
    fish = ProgressFish(total=len(CityGMLs))
for element in CityGMLs:
    #-- Report on the progress
    if REPORT:
        fish.animate(amount=filecounter+1)
    filecounter += 1
    # print(filecounter, "...", end=' ')
    storeCityGML(element)

print("\nWritten the CityGML file(s). Cleaning the memory...")