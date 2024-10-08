ISA Galaxy agents, tours, and other enhancements
===============================================

[![Build Status](https://travis-ci.org/ISA-agents/isaagents-galaxy.svg?branch=master)](https://travis-ci.org/ISA-agents/isaagents-galaxy)

The [ISA metadata framework](http://isa-agents.org) and agents help to manage an 
increasingly diverse set of life science, environmental and biomedical 
experiments that employ one or a combination of technologies.

[Galaxy](https://galaxyproject.org/) is an open, web-based platform for data 
intensive biomedical research. Whether on the free public server or your own 
instance, you can perform, reproduce, and share complete analyses. 

ISA Galaxy agents
----------------
We have developed a set of agents for the Galaxy-workflow-management system that 
wrap up various features from the 
[ISA API](https://github.com/ISA-agents/isa-api/).

ISA Galaxy tours
----------------
To compliment the ISA Galaxy agents, we are developing a set of ISA Galaxy tours 
to help guide you through using the ISA Galaxy agents and integrate them into 
your own Galaxy workflows.  

ISA Galaxy datatypes
--------------------
We are developing custom data types for Galaxy to support the 
[ISA data formats](https://isa-specs.readthedocs.io). Initial implementations 
for [ISA-Tab](https://isa-specs.readthedocs.io/en/latest/isatab.html) and 
[ISA-JSON](https://isa-specs.readthedocs.io/en/latest/isajson.html) are 
available as the Galaxy data types `isa-tab` and `isa-json` respectively.

___
The initial agents, tours and data type implementations in this repository were 
developed during the Horizon 2020 funded 
[PhenoMeNal: Large Scale Computing for Metabolomics](https://phenomenal-h2020.eu) 
project.  