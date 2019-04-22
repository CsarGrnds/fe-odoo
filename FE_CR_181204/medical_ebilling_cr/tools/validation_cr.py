# -*- coding: utf-8 -*-
###################################################
#
#    Account Invoice Retention MODULE
#    Copyright (C) 2012 Atikasoft Cia.Ltda. (<http://www.atikasoft.com.ec>).
#    $autor: Dairon Medina Caro <dairon.medina@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###################################################

def cedula_01_validation(identification_number):
    if identification_number:
        numcc = identification_number
        firts_three = numcc[0:3]
        total_three = 0
        for el_three in firts_three:
            total_three += int(el_three)
        if total_three != 0:
            return False
    return True

def cedula_02_validation(identification_number):
    if identification_number:
        numcc = identification_number
        firts_twoo = numcc[0:2]
        total_twoo = 0
        for el_twoo in firts_twoo:
            total_twoo += int(el_twoo)
        if total_twoo != 0:
            return False
    return True

def dimex_validation(identification_number):
    if identification_number:
        numcc = identification_number
        firts_one = numcc[0:1]
        if int(firts_one) != 0:
            return False
    return True

def nite_validation(identification_number):
    if identification_number:
        numcc = identification_number
        firts_twoo = numcc[0:2]
        total_twoo = 0
        for el_twoo in firts_twoo:
            total_twoo += int(el_twoo)
        if total_twoo != 0:
            return False
    return True