#!/usr/bin/env python
# encoding: utf-8

## Copyright 2011 Ryan Orendorff, NCAR under GPLv3
## See README.mkd for more details.

## Objects designed to hold data from the EOL PSQL live repository. The
## NVar class is designed to hold one varibles information, in the order it
## was added to the object, and along with a timestamp for the data.
##
## This information can then be sliced out (without the datetime stamp)
## or sliced as a list of tuples that includes the datetime using
## sliceWithTime(). Slices can be done either through integer indexes that are
## related to the order of entry (so `NVar[-2:]` provides the last two data
## entries) or with a datetime object (`NVar[time:]` returns all data from
## `time` on, where `time` must exist). These methods can be mixed and matched
## (`NVar[time,-1]`)
##
## The NVarSet holds a set of NVar objects and allows the entire set to be
## sliced in the same manner as mentioned above, returning a list of tuples
## where each column represents one NVar. The order is determined by entry
## into the set.
##
## Both classes are designed to act like a tuple in the fact that they are
## READ ONLY! If you would like to add data to a NVar or NVarSet (for NVar
## this can be done with `+` operator) a new instance of the class must
## be created. This design was chosen to preserve the data's integrity,
## preventing accidental overwrites.
##
## Author: Ryan Orendorff <ryano@ucar.edu>
## Date: 30/08/11 13:14:44

## TODO: Either make _addData functions private or subclass the variable sets
## for real time use

## --------------------------------------------------------------------------
## Imports and Globals
## --------------------------------------------------------------------------

## Intrapackage imports
from datafile import NRTFile

## New data type, not supported below python 2.7
from collections import OrderedDict

import datetime

## --------------------------------------------------------------------------
## Functions
## --------------------------------------------------------------------------


def createOrderedList(variables):
    """
    Creates a list where col[0] is the variable name and
    col[1] is an NVar object.
    """
    var_list = []
    for var in variables:
        var_list.append((var.lower(), NVar(var)))

    return var_list


def createOrderedListFromFile(file_name):
    nfile = NRTFile(file_name)
    olist = NVarSet(nfile.labels[1:])
    olist.addData(nfile.data)
    return olist


## --------------------------------------------------------------------------
## Classes
## --------------------------------------------------------------------------


class NVarSet(OrderedDict):
    """
    Holds multiple NVars, and assumes that they are all the same size (this is
    true from live aircraft data). Can export data as a list using .data
    """

    def __init__(self, var_start, *variables):
        """
        Init function can take either a python list of variables or every
        variable listed as a parameter.
        """
        self._str = None

        def _isNVar():
            var_list = []
            for var in var_start:
                var_list.append((var.name, var))

            return var_list

        ## If input is just NVarSet('var1','var2'), convert into list
        if isinstance(var_start, list) and variables == ():
            if isinstance(var_start[0], NVar):
                var_list = _isNVar()
            else:
                var_list = createOrderedList(tuple(var_start))
        elif isinstance(var_start, tuple) and variables == ():
            if isinstance(var_start[0], NVar):
                var_list = _isNVar()
            else:
                var_list = createOrderedList(var_start)
        else:
            var_list = createOrderedList((var_start,) + variables)

        self._str = str([var[0] for var in var_list])
        self._time = var_list[0][1]
        super(NVarSet, self).__init__(var_list)

    def __str__(self):
        return "NVarSet%s" % self._str

    def __getitem__(self, item):
        if isinstance(item, slice):
            data = []

            start, stop = self.__sliceToIndex(item)
            for counter in xrange(start, stop):
                data += (self.__getLine(pos=counter, add_time=False), )

            return data

        else:
            return self.__getLine(pos=item, add_time=False)

    def sliceWithTime(self, *args):
        if len(args) == 1:
            slc = slice(None, args[0], None)
        elif len(args) == 2:
            slc = slice(args[0], args[1], None)
        else:
            raise ValueError('sliceWithTime only accepts stop '
                             'or start, stop arguments')
        data = []

        start, stop = self.__sliceToIndex(slc)
        for counter in xrange(start, stop):
            data += (self.__getLine(pos=counter, add_time=True), )

        return data

    def __getLine(self, pos=None, add_time=False):
        if add_time is False:
            line = ()
        else:
            line = (self._time.getTimeFromPos(pos), )

        for var in OrderedDict.__iter__(self):
            line += (OrderedDict.__getitem__(self, var)[pos],)

        return line

    def __sliceToIndex(self, item):
        start = stop = None

        if isinstance(item.start, datetime.datetime):
            start = self._time.getPosFromTime(item.start)
        else:
            if item.start is None:
                start = 0
            else:
                if item.start < 0:
                    start = len(self._time) + item.start
                else:
                    start = item.start

        if isinstance(item.stop, datetime.datetime):
            stop = self._pos_of_date[item.stop]
        else:
            if item.stop is None:
                stop = len(self._time)
            else:
                if item.stop < 0:
                    stop = len(self._time) + item.stop
                else:
                    stop = item.stop

        return start, stop

    def addData(self, data):
        """
        Adds data to the set. Must match the variable order of the set and the
        number of variables in the set.
        """
        if len(data) != 0:
            pos = 1
            for var in OrderedDict.__iter__(self):
                (OrderedDict.__getitem__(self, var).
                 addData([(column[0], column[pos]) for column in data]))
                pos += 1

    @property
    def labels(self):
        """ Return the names associated with the columns in .data """
        return tuple(['DATETIME'] + self.keys())

    def getNVar(self, name):
        return OrderedDict.__getitem__(self, name)


class NVar(OrderedDict):
    """
    The basic class for holding chronological list data. It is accessed like a
    dictionary where the datetime is the key. It will also ordered, so using an
    integer as the key will give the Nth value in the list. Only accepts one
    data value per datetime.
    """

    def __init__(self, name=None):
        self.name = name.lower()
        self._time_of_pos = {}  # {position: datetime}
        self._pos_of_time = {}  # {datetime: position}
        super(NVar, self).__init__()

    def __getitem__(self, item):
        if isinstance(item, slice):
            data = []

            start, stop = self.__sliceToIndex(item)
            for point in xrange(start, stop):
                data += [self.__getitem__(point)]

            return data
        if isinstance(item, int):
            if item < 0:
                return (OrderedDict.__getitem__(self,
                        self._time_of_pos[(OrderedDict.__len__(self)) + item]))
            else:
                return OrderedDict.__getitem__(self, self._time_of_pos[item])
        else:
            return OrderedDict.__getitem__(self, item)

    def sliceWithTime(self, *args):
        if len(args) == 1:
            slc = slice(None, args[0], None)
        elif len(args) == 2:
            slc = slice(args[0], args[1], None)
        else:
            raise ValueError('sliceWithTime only accepts '
                             'stop or start, stop arguments')

        data = []

        start, stop = self.__sliceToIndex(slc)
        for point in xrange(start, stop):
            data += [(self.getTimeFromPos(point), self.__getitem__(point))]

        return data

    def __sliceToIndex(self, item):
        start = stop = None

        if isinstance(item.start, datetime.datetime):
            start = self._pos_of_time[item.start]
        else:
            if item.start is None:
                start = 0
            else:
                if item.start < 0:
                    start = OrderedDict.__len__(self) + item.start
                else:
                    start = item.start

        if isinstance(item.stop, datetime.datetime):
            stop = self._pos_of_time[item.stop]
        else:
            if item.stop is None:
                stop = OrderedDict.__len__(self)
            else:
                if item.stop < 0:
                    stop = OrderedDict.__len__(self) + item.stop
                else:
                    stop = item.stop

        return start, stop

    def __add__(self, y):
        data = []

        name = None
        x_name = self.name
        y_name = None

        for k, v in self.iteritems():
            data += [(k, v)]

        if isinstance(y, NVar):
            y_name = y.name
            for k, v in y.iteritems():
                data += [(k, v)]
        else:
            data += y

        data.sort(key=lambda x: x[0])

        if x_name == y_name and (x_name is not None and y_name is not None):
            name = x_name
        elif x_name is not None and y_name is None:
            name = x_name
        elif x_name is None and y_name is not None:
            name = y_name
        else:
            raise ValueError('NVar: can only add NVars of the same name.')

        if name is not None:
            var = NVar(name)
            var.addData(data)
            return var

    def getTimeFromPos(self, index):
        """ Returns the date associated with an integer index. """
        if index < 0:
            return self._time_of_pos[(OrderedDict.__len__(self)) + index]
        else:
            return self._time_of_pos[index]

    def getPosFromTime(self, tm):
        return self._pos_of_time[tm]

    def addData(self, data=[]):
        """
        Adds data to the variable. It does not check the data input, this must
        be done prior to adding the data.
        """
        if len(data) == 0:
            return

        try:
            if not isinstance(data[0][0], datetime.datetime):
                raise ValueError
            try:
                data[0][1]
            except Exception:
                raise ValueError

        except ValueError, e:
            raise ValueError('NVar: Data must be formatted as '
                             '[(datetime, value), ...]')

        for row in data:
            self._time_of_pos[OrderedDict.__len__(self)] = row[0]
            self._pos_of_time[row[0]] = OrderedDict.__len__(self)
            OrderedDict.__setitem__(self, row[0], row[1])
