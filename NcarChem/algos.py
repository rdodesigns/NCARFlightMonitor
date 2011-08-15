#!/usr/bin/env python
# encoding: utf-8

## Test of live data reading.
##
## Author: Ryan Orendorff <ryano@ucar.edu>
## Date: 21/07/11 10:31:47
##

## Syntax notes for coders who are not author
## - A double pound (##) is a comment, a single is commented code


## --------------------------------------------------------------------------
## Imports and Globals
## --------------------------------------------------------------------------

## Time based imports
import datetime

## --------------------------------------------------------------------------
## Classes
## --------------------------------------------------------------------------
class NAlgorithm(object):
  """
  A container class for processing data. Users are meant to place a processing
  algorithm in either an instance of the class or the class itself (as a
  process() function). This function does not currenetly accept parameters.
  """
  def __init__(self):
    self.error = False  ## Used for error checking, caling, etc
    self.last_date = datetime.datetime(1970, 1, 1, 0, 0, 0)
    self.variables = []  ## NVar type
    self.updated = False

    self.setup = lambda : None
    self.process = lambda : None

  def run(self):
    new_date = self.variables[0].getDate(-1)
    if new_date > self.last_date:
      self.updated = True
      self.process()
      self.last_date = new_date
    else:
      self.updated = False

  def reset(self):
    try:
      self.setup()
    except Exception, e:
      print "Could not rerun setup command."
      print e
