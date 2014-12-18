Random3Dcity
============

A procedural modelling engine for generating buildings and other features in CityGML in multiple levels of detail (LOD).

![Overview](http://3dgeoinfo.bk.tudelft.nl/biljecki/code/img/R3-interior.png)


# Ready to use datasets

If you are interested only in the datasets, without the need to run the code, please visit my personal webpage to download a prepared collection of datasets: [http://3dgeoinfo.bk.tudelft.nl/biljecki/Random3Dcity.html](http://3dgeoinfo.bk.tudelft.nl/biljecki/Random3Dcity.html)

# Introduction

This experimental software prototype was developed as a part of my [PhD research](http://3dgeoinfo.bk.tudelft.nl/biljecki/phd.html), and it has been designed and developed from scratch.

Procedural modelling engines natively supporting CityGML and designed for generating semantically structured 3D city models in multiple LODs are not available. This project presents an effort to fill this gap.

The engine is composed of two modules. The first one is procedural: it randomly generates buildings and their elements according to a comprehensive set of rules and constraints. The buildings are realised through parametres which are stored in an XML form.

The second part of the engine reads this data and constructs CityGML data in multiple LODs.


## Conditions for use


This software is free to use. However, you are kindly requested to acknowledge the use of this software by citing it in a research paper you are writing, reports, and/or other applicable materials; and mentioning the [3D Geoinformation group at the Delft University of Technology](http://3dgeoinfo.bk.tudelft.nl/). A research paper is under submission, hence please contact me to give you a reference to cite.

Further, I will be very happy to hear if you find this tool useful for your workflow. If you find it useful and/or have suggestions for its improvement, please let me know. Further, I am maintaining a list of users that I notify of corrections and updates.


## Academic reference with a detailed methodology

Coming soon. Journal paper under submission.

System requirements
---------------------

Python packages:

+ [Numpy](http://docs.scipy.org/doc/numpy/user/install.html) (likely already on your system)
+ [lxml](http://lxml.de)

### OS and Python version
  
The software has been developed on Mac OSX in Python 2.7, and has not been tested with other configurations. Hence, it is possible that some of the functions will not work on Windows and on Python 3.

## Features and technical details

### Roof types and building parts

The engine supports five types of roofs: flat, gabled, hipped, pyramidal, and shed. Further, it supports also building parts such as garages and alcoves.

![Roofs](http://3dgeoinfo.bk.tudelft.nl/biljecki/code/img/R3-roofTypes.png)


### 16 Levels of detail

The engine supports generating data in 16 levels of detail. The following composite render shows an example of four LODs:

![LOD-composite](http://3dgeoinfo.bk.tudelft.nl/biljecki/code/img/R3-LOD-composite.png)

The following image shows the specification of our novel LOD specification ("Delft LODs") according to which the models are generated. This specification will be published in details.

![LOD-refined-specification](http://3dgeoinfo.bk.tudelft.nl/biljecki/code/img/R3-refinedLODs_.png)

### Geometric references

Besides the LODs, the engine generates multiple representations according to geometric references within LODs, e.g. an LOD1 with varying heights of the top surface (height at the eaves, at the half of the roof, etc.)

![Geometric references](http://3dgeoinfo.bk.tudelft.nl/biljecki/code/img/R3-LOD1cb.png)


### Solids

Each representation is constructed its corresponding solid.

![Solids](http://3dgeoinfo.bk.tudelft.nl/biljecki/code/img/R3-assemblingSolid.png)


### Vegetation and streets

An experimental feature is the generation of vegetation and streets.

![Other-features](http://3dgeoinfo.bk.tudelft.nl/biljecki/code/img/R3-roads.png)


### Interior of buildings

A basic interior of buildings in three LODs may be generated: see the header in the attachment. This is based on another paper from my group that deals with the refinement of the level of detail concept for interior features. Besides the solids for each floor, a 2D representation per each storey, and a solid for the whole building (offset from the walls) may be generated.

Documented uses
---------------------

Besides my [PhD](http://3dgeoinfo.bk.tudelft.nl/biljecki/phd.html) in which I did a lot of experiments and benchmarking with CityGML data, the engine has been used for testing validation and repair software, and other purposes such as error propagation. For the full showcase visit the [data page](http://3dgeoinfo.bk.tudelft.nl/biljecki/Random3Dcity.html).


Usage and options
---------------------

### Introduction to randomising the city

To generate buildings run

```
python randomiseCity.py -o /path/to/the/building/file.xml -n 4000
```

where `n` is the number of buildings to be generated. If you don't specify the number of buildings, by default the program will generate 1000 buildings.

To realise these buildings as a 3D city model in CityGML in multiple levels of detail run:

```
python generateCityGML.py -i /path/to/the/building/file.xml -o /path/to/CityGML/directory/
```
Don't forget to put the `/` at the end of the directory.

### Rotation

If you want to have the buildings rotated randomly, in both commands toggle the flag `-r 1`.

### Building parts

Building parts are generated with the flag `-p 1`.

### Vegetation and street network

Vegetation and street network are generated with the flags `-v 1` and `-s 1`, respectively.

### Solids and geometric references

`generateCityGML.py` generates solids with the option `-ov 1`, and all geometric references with `-gr 1`.

### gml:id according to UUID

It is possible to generate an UUID for each <gml:Polygon> with the option `-id 1`.

### Coordinate system

If you run the building randomiser with the option `-c 1`, the buildings will be placed in the Dutch coordinate system (RD new), somewhere in the Nordoostpolder in the Netherlands. You can easily customise this in the code.

Performance
---------------------

The speed mainly depends on the invoked options. With all the options the engine generates around 100 buildings per minute. The computational complexity is not strictly linear, and a high number of buildings (>20000) will likely eat all of your RAM making the process slower.

Known issues
---------------------

### CityGML issues

+ The output files are stored in CityGML 2.0. Output in the legacy versions 0.4 and 1.0 is not available.
+ There are multiple MultiSurface instances within the same thematic boundary (boundedBy), which might cause problems for some software packages. This will be fixed in the next version.

### Python issues

+ This software has been programmed with Python 2.7. Version 3 is not supported.

### Running issues

The `generateCityGML.py` program has been known to crash in two cases:

+ It runs out of memory if too many buildings are attempted to be generated in CityGML. Reduce the number of buildings and/or their variants (e.g. disable the generation of solids).
+ Uncommonly it crashes when it encounters a very peculiar building to be generated. This does not happen often, and when it does just generate a new set of buildings with `randomiseCity.py`.


Special datasets
---------------------

I have prepared a number of intentionally impaired datasets suited for different types of experiments, such as overlapping buildings and simulated geometric errors. For the full list visit the [data page](http://3dgeoinfo.bk.tudelft.nl/biljecki/Random3Dcity.html)

![Intentional errors](http://3dgeoinfo.bk.tudelft.nl/biljecki/random3dcity/errors/overlapping/overlapping.png)


Contact me for questions and feedback
---------------------
Filip Biljecki

[3D Geoinformation Research Group](http://3dgeoinfo.bk.tudelft.nl/)

Faculty of Architecture and the Built Environment

Delft University of Technology

email: fbiljecki at gmail dot com

[Personal webpage](http://3dgeoinfo.bk.tudelft.nl/biljecki/)


# Acknowledgments

+ This research is supported by the Dutch Technology Foundation STW, which is part of the Netherlands Organisation for Scientific Research (NWO), and which is partly funded by the Ministry of Economic Affairs. (Project code: 11300)

+ People who gave suggestions and reported errors