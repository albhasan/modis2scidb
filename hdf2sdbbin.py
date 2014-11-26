import os
import sys
import fnmatch
import subprocess
import datetime
import argparse
import logging
import re


def isLeapYear(year):
	'''Returns TRUE if the given year (int) is leap and FALSE otherwise'''
	leapyear = False
	if year % 4 != 0:
		leapyear = False
	elif year % 100 != 0:
		leapyear = True
	elif year % 400 == 0:
		leapyear = True
	else:
		leapyear = False
	return leapyear


def listFiles(path, pattern):
	res = list()
	for path, subdirs, files in os.walk(path):
		for name in files:
			filepath = os.path.join(path, name)
			if(re.match(pattern, filepath, flags=0)):
				res.append(filepath)
	return res

	
def testGribModis2SciDB():
	'''Test if GRibeiro's modis2scidb is installed'''
	res = True
	try:
		subprocess.check_output(["modis2scidb", "--h"])
	except:
		res = False
	return res

	
def date2grid(dateFileName, period, startyear):
	'''Return an time index (timid) from the input date (MODIS DOY) and time period (e.g 8 days). '''
	res = -1
	if period > 0:
		dateYYYYDOY = dateFileName[1:] #Remove the A precedding the date
		year = int(dateYYYYDOY[0:4])
		doy = int(dateYYYYDOY[4:7])
		ppy = int(365 / period) + 1 # Periods per year
		if(period > 0 and (doy - 1) % period == 0):
			idd = (doy - 1) / period
			idy = (year - startyear) * ppy
			res = idy + idd
		else:
			logging.error("date2grid: Invalid date")
	elif period == -319980101: # Monthly - given as YYYYMMDD i.e 19980101, 19980201, 19980301
		dateYYYYMMDD = dateFileName
		year = int(dateYYYYMMDD[0:4])
		mm = int(dateYYYYMMDD[4:6])
		#dd = int(dateYYYYMMDD[6:8])
		idy = (year - startyear) * 12
		idd = mm - 1
		res = idy + idd
	return res	


#********************************************************
# MAIN
#********************************************************
def main(argv):
	t0 = datetime.datetime.now()
	parser = argparse.ArgumentParser(description = "Exports MODIS-HDFs to binary files for uploading to SCIDB using GRibeiro's tool")
	parser.add_argument("hdfFile", help = "Path to the HDF")
	parser.add_argument("loadFolder", help = "Folder from where the binary files are uploaded to SCIDB")
	parser.add_argument("product", help = "Product. e.g MOD09Q1")
	parser.add_argument("--log", help = "Log level. Default = WARNING", default = 'WARNING')
	#Get paramters
	args = parser.parse_args()
	hdfFile = os.path.join(args.hdfFile, '')
	loadFolder = os.path.join(args.loadFolder, '')
	product = args.product
	log = args.log
	####################################################
	# CONFIG
	####################################################
	prodList = ['MOD09Q1', 'MOD13Q1', 'TRMM3B43']
	prodTemporalResolution = {
		'MOD09Q1':	8,
		'MOD13Q1':	16,
		'TRMM3B43':	-319980101
	}
	prodStartYear = {
		'MOD09Q1':	2000,
		'MOD13Q1':	2000,
		'TRMM3B43':	1998
	}
	prodBands = {
		'MOD09Q1':	'0,1,2',
		'MOD13Q1':	'0,1,2,3,4,5,6,7,8,9,10,11',
		'TRMM3B43':	'0,1,2'
	}
	numeric_loglevel = getattr(logging, log.upper(), None)
	if not isinstance(numeric_loglevel, int):
		raise ValueError('Invalid log level: %s' % log)
	logging.basicConfig(filename = 'log_hdf2sdbin.log', level = numeric_loglevel, format = '%(asctime)s %(levelname)s: %(message)s')
	logging.info("log_hdf2sdbin.py: " + str(args))
	####################################################
	# VALIDATION
	####################################################
	if product in prodList == False:
		logging.exception("Unknown product!")
		raise Exception("Unknown product!")
	if testGribModis2SciDB() == False:
		logging.exception("GRibeiro's mod2scidb not found")
		raise Exception("GRibeiro's mod2scidb not found")
	####################################################
	# 
	####################################################
	cmd = ""
	try:
		period = prodTemporalResolution[product]
		startyear = prodStartYear[product]
		bands = prodBands[product]

		filename = os.path.basename(hdfFile)
		time_id = date2grid(filename.split(".")[1], period, startyear)
		arg0 = "modis2scidb"
		arg1 = " --f " + hdfFile
		arg2 = " --o " + loadFolder + os.path.splitext(filename)[0] + ".sdbbin"
		arg3 = " --b " + bands
		arg4 = " --t " + str(time_id)
		cmd = arg0 + arg1 + arg2 + arg3 + arg4
		subprocess.check_call(str(cmd), shell = True)
	except subp.CalledProcessError as e:
		logging.exception("CalledProcessError: " + cmd + "\n" + str(e.message))
	except ValueError as e:
		logging.exception("ValueError: " + cmd + "\n" + str(e.message))
	except OSError as e:
		logging.exception("OSError: " + cmd + "\n" + str(e.message))
	except:
		e = sys.exc_info()[0]
		logging.exception("Unknown exception: " + cmd + "\n" + str(e.message))

	t1 = datetime.datetime.now()	
	tt = t1 - t0
	logging.info("Finished in " + str(tt))
	

if __name__ == "__main__":
   main(sys.argv[1:])
   
   
   
   
