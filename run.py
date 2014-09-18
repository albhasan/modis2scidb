import os
import sys
import fnmatch
import subprocess as subp
import datetime
import argparse
import logging



#********************************************************
# UTIL
#********************************************************
def buildPath(path):
	res = path
	if path[len(path) - 1] != '/':
		res = path + '/'
	return res

def buildDoy(yearFrom, yearTo, period):
	'''Returns an int array containing the year-day-of-the-year set corresponding to the given year interval'''
	res = []
	
	for year in range(yearFrom, yearTo + 1):
		byear = year * 1000
		for i in range(0, 365/period + 1):
			res.append(byear + 1 + i * period)
	return res
	
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
	
def doy2date(yyyydoy):
	'''Returns an int array year-month-day (e.g [2001, 1, 1]) out of the given year-day-of-the-year (e.g 2001001)'''
	if len(str(yyyydoy)) == 7:
		year = int(str(yyyydoy)[:4])
		doy = int(str(yyyydoy)[4:])
		if doy > 0 and doy < 367:
			firstdayRegular = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335, 366]
			firstdayLeap = [1, 32, 61, 92, 122, 153, 183, 214, 245, 275, 306, 336, 367]
			if isLeapYear(year):
				firstday = firstdayLeap
			else:
				firstday = firstdayRegular
			for i in range(len(firstday) - 1):
				start = firstday[i]
				end = firstday[i + 1]
				if doy >= start and doy < end:
					month = i + 1
					break
			day = doy - firstday[month - 1] + 1
		res = [year, month, day]
	return res

def getHV(tile):
	'''Returns the h and v components (i.e ['08', '10']) from the given tile id. Use map to get int instead of strings. results = map(int, results)'''
	h = tile[1:3]
	v = tile[4:6]
	return [h, v]
	
def checkHdfName(file, head, yyyydoyFrom, yyyydoyTo, hFrom, hTo, vFrom, vTo, col, ext):
	'''Returns TRUE if the given file name (e.g MOD09Q1.A2013361.h13v10.005.2014006133008.hdf) fits in the given parameters'''
	res = False
	fnparts = file.split(".")
	if len(fnparts) == 6:
		yyydoy = int(fnparts[1][1:])
		if yyydoy >= yyyydoyFrom and yyydoy <= yyyydoyTo:
			hv = map(int, getHV(fnparts[2]))
			h = hv[0]
			v = hv[1]
			if h >= hFrom and h <= hTo and v >= vFrom and v <= vTo:
				if fnparts[0] == head:
					if fnparts[3] == col:
						if fnparts[5] == ext:
							res = True
	return res
	
def checkHdfName(file, head, Adoy, tile, col, ext):
	'''Checks filename for the right number of parts, extension, date (YYYDOY), tile, name start and collection'''
	res = False
	fnparts = file.split(".")
	if len(fnparts) == 6:
		if fnparts[1] == Adoy:
			if fnparts[2] == tile:
				if fnparts[0] == head:
					if fnparts[3] == col:
						if fnparts[5] == ext:
							res = True
	return res

def checkHdfName(file, splitStr, nParts, ext):
	'''Returns TRUE if the given filename has the right number of parts and extension. It returns FALSE otherwise'''
	res = False
	p = file.split(splitStr)
	if len(p) == nParts:
		if p[len(p) - 1] == ext:
			res = True
	return res

def isStringinList(aString, strList):
	'''Returns TRUE if the given string is part of the given list and FALSE otherwise'''
	res = False
	for s in strList:
		if aString == s:
			res = True
			break
	return res

def buildAdoyList(doyList):
	'''Returns the list adding an "A" to each element'''
	res = []
	for doy in doyList:
		res.append('A' + str(doy))
	return res;

def buildTileLits(hRange, vRange):
	'''Return a list of MODIS tile names built from the given ranges'''
	res = []
	for h in hRange:
		for v in vRange:
			htmp = str(h)
			vtmp = str(v)
			if len(htmp) < 2:
				htmp = '0' + htmp
			if len(vtmp) < 2:
				vtmp = '0' + vtmp
			tmp = 'h' + htmp + 'v' + vtmp
			res.append(tmp)
	return res
	
def buildBinaryFilePath(basebfilepath, hRange, vRange, date, prod):
	'''Returns a name for a binary file made of a set of tiles'''
	tmpfn = 0
	for i in hRange:
		for j in vRange:
			tmpfn = tmpfn + i + j
	binaryFilename = 'load_' + prod + str(tmpfn) + str(date) + '.sdbbin'
	res = basebfilepath + binaryFilename
	return res

def buildBinaryFilePath1(basebfilepath, h, v, date):
	'''Builds the name of a single binary file'''
	hn = str(h)
	vn = str(v)
	if len(hn) == 1:
		hn = 'h0' + hn
	elif len(hn) == 2:
		hn = 'h' + hn
	if len(vn) == 1:
		vn = 'v0' + vn
	elif len(vn) == 2:
		vn = 'v' + vn
	binaryFilename = 'load_' + hn + vn + '_' + str(date) + '.sdbbin'
	res = basebfilepath + binaryFilename
	return res

def buildTileName(h, v):
	'''Returns a tile name from the given parameters'''
	si = ''
	sj = ''
	if len(str(h)) == 1:
		si = 'h0' + h
	else:
		si = 'h' + str(h)
	if len(str(v)) == 1:
		sj = 'v0' + str(v)
	else:
		sj = 'v' + str(v)
	res = si + sj
	return res

def callAddHdfCommand(scriptFolder, hdf2binFolder, loadFolder, hdfPaths, binaryFilepath, lineMin, lineMax, sampMin, sampMax, period, log):
	'''Calls the script that builds the binary files from HDFs'''
	arg0 = "python " + scriptFolder + "addHdfs2bin.py --log INFO "
	arg1 = ';'.join(hdfPaths)
	arg2 = " " + binaryFilepath
	arg3 = " --lineMin " + str(lineMin)
	arg4 = " --lineMax " + str(lineMax)
	arg5 = " --sampMin " + str(sampMin)
	arg6 = " --sampMax " + str(sampMax)
	arg7 = " --period " + str(period)
	arg8 = " --log " + log
	cmd = arg0 + arg3 + arg4 + arg5 + arg6 + arg7 + arg8 + ' "' + arg1 + '"' + arg2
	logging.info("Calling addHdf: " + cmd)
	subp.check_call(str(cmd), shell=True)
	#Copy to the keep folder
	tmpPts = binaryFilepath.split("/")
	fn = tmpPts[len(tmpPts) - 1]
	if os.path.isfile(binaryFilepath):
		if os.path.isdir(hdf2binFolder):
			cmd1 = "cp " + binaryFilepath + " " + buildPath(hdf2binFolder) + fn
			logging.info("Copying binary file to KEEP folder..: " + cmd1)
			subp.check_call(str(cmd1), shell=True)
		#Move file to the loadFolder folder
		cmd2 = "mv " + binaryFilepath + " " + loadFolder + os.path.basename(binaryFilepath)
		logging.info("Moving binary file to LOAD folder..: " + cmd2)
		subp.check_call(str(cmd2), shell=True)
	else:
		logging.warning("File not found: " + binaryFilepath)
		
	
def loadhdfCHRONOS(modisPath, basebfilepath, dates, hRange, vRange, hdf2binFolder, loadFolder, scriptFolder, lineMin, lineMax, sampMin, sampMax, period, prod, log):
	'''Builds the file paths and calls the load script. The paths match the storage folder schema .../modisProductPath/year/HDFs'''
	hdflist = []
	#head = 'MOD09Q1'
	#col = '005'
	ext = 'hdf'
	splitStr = '.'
	nParts = 6
	tilelist = buildTileLits(hRange, vRange)
	
	for date in dates:
		hdfPaths = []
		hdfFiles = []
		hdfFilesExt = []
		hdfFilesExtDoy = []
		#Builds the basepath where to find the HDFs
		d = doy2date(date)
		adoyList = buildAdoyList([date])
		yyyy = d[0]
		#basePath = modisPath + str(yyyy) + '/250m/'
		basePath = modisPath + str(yyyy) + '/'
		if os.path.isdir(basePath):
			dirs = os.listdir( basePath )
			#Builds the name of the binary file
			binaryFilepath = buildBinaryFilePath(basebfilepath, hRange, vRange, date, prod)
			#Get the path to the HDFs
			for f in dirs:
				if checkHdfName(f, splitStr, nParts, ext):#Filter by number of parts and file extension
					hdfFilesExt.append(f)
			for f in hdfFilesExt:
				if f.split(".")[1] in adoyList:#Filter by DOY
					hdfFilesExtDoy.append(f)
			for f in hdfFilesExtDoy:
				if f.split(".")[2] in tilelist:#Filter by TILE
					hdfFiles.append(f)
			#Add the path to each file
			for f in hdfFiles:
				hdfPaths.append(basePath + f)
			#Command
			if len(hdfPaths) > 0:
				callAddHdfCommand(scriptFolder, hdf2binFolder, loadFolder, hdfPaths, binaryFilepath, lineMin, lineMax, sampMin, sampMax, period, log)
			else:
				logging.warning("No HDF file match the given DOY and TILE")
		else:
			logging.warning("Not a directory: " + basePath)


def loadhdfModisPackage(modisPath, basebfilepath, dates, hRange, vRange, hdf2binFolder, loadFolder, scriptFolder, lineMin, lineMax, sampMin, sampMax, period, prod, log):
	'''Builds the file paths and calls the load script. The paths match the storage folder schema of R' MODIS package'''
	for date in dates:
		hdfPaths = []
		#Builds the basepath where to find the HDFs
		d = doy2date(date)
		yyyy = d[0]
		mm = d[1]
		dd = d[2]
		if len(str(d[1])) == 1:
			mm = '0'  +str(d[1])
		if len(str(d[2])) == 1:
			dd = '0' + str(d[2])
		basePath = modisPath + str(yyyy) + '.'  + str(mm) + '.'  + str(dd) + '/'
		if os.path.isdir(basePath):
			#Builds the name of the binary file
			binaryFilepath = buildBinaryFilePath(basebfilepath, hRange, vRange, date, prod)
			#Get the path to the HDFs
			for i in hRange:
				for j in vRange:
					tile = '*' + buildTileName(i, j) + '*'
					for file in os.listdir(basePath):
						if fnmatch.fnmatch(file, tile):
							if fnmatch.fnmatch(file, '*' + str(date) + '*'):
								hdfPaths.append(basePath + file)
			#Command
			callAddHdfCommand(scriptFolder, hdf2binFolder, loadFolder, hdfPaths, binaryFilepath, lineMin, lineMax, sampMin, sampMax, period, log)

			
#********************************************************
#WORKER
#********************************************************
def main(argv):
	t0 = datetime.datetime.now()
	parser = argparse.ArgumentParser(description = "Exports MODIS-HDFs to binary files for uploading to SCIDB")
	parser.add_argument("modisPath", help = "Path to the folder containing the MODIS HDFs")
	parser.add_argument("modisFolderSchema", help = "Folder structure for storing HDFs. R-MODIS for the R MODIS package structure. MP-YEAR for /modisProduct/year/hdf", choices=['R-MODIS', 'MP-YEAR'])
	parser.add_argument("basebfilepath", help = "Folder to temporally store the resulting binary files")
	parser.add_argument("loadFolder", help = "Folder from where the binary files are uploaded to SCIDB")
	#parser.add_argument("scriptFolder", help = "Folder containing pythons scripts")
	parser.add_argument("hMin", help = "Min H tile value", type = int)
	parser.add_argument("hMax", help = "Max H tile value", type = int)
	parser.add_argument("vMin", help = "Min V tile value", type = int)
	parser.add_argument("vMax", help = "Max V tile value", type = int)
	parser.add_argument("-p", "--product", help = "MODIS product. e.g MOD09Q1", default = "default")
	parser.add_argument("-yf", "--yearFrom", help = "Starting year of data. Default = 2000", type = int, default = 2000)
	parser.add_argument("-yt", "--yearTo", help = "End year of data. Default = 2013", type = int, default = 2013)
	parser.add_argument("-h2b", "--hdf2binFolder", help = "Folder to keep a copy of the binary files", default = '')	
	parser.add_argument("--log", help = "Log level. Default = WARNING", default = 'WARNING')
	#Get paramters
	args = parser.parse_args()
	modisPath = args.modisPath
	modisFolderSchema = args.modisFolderSchema
	basebfilepath = args.basebfilepath
	loadFolder = args.loadFolder
	scriptFolder = buildPath(sys.path[0])
	# args.scriptFolder
	hMin = args.hMin
	hMax = args.hMax
	vMin = args.vMin
	vMax = args.vMax
	hRange = range(hMin,hMax)
	vRange = range(vMin,vMax)
	prod = args.product
	yearFrom = args.yearFrom
	yearTo = args.yearTo
	hdf2binFolder = args.hdf2binFolder
	log = args.log
	####################################################
	# CONFIG
	####################################################
	modisprod = ['MOD09Q1', 'MOD13Q1']
	temporalResolution = {
		'MOD09Q1': 8,
		'MOD13Q1': 16
	}
	if prod == 'default':
		for mp in modisprod:
			if mp in modisPath:
				prod = mp
	if prod in modisprod == False:
		logging.exception("Unknown MODIS product: The MODIS product could not be figured out.")
		raise Exception("Unknown MODIS product")
	period = temporalResolution[prod]
	# Pixel interval
	lineMin = 0
	lineMax = 4799
	sampMin = 0
	sampMax = 4799
	dates = buildDoy(yearFrom, yearTo, period)
	if yearFrom == 2000:
		dates = buildDoy(yearFrom, yearTo, period)
	#Log
	numeric_loglevel = getattr(logging, log.upper(), None)
	if not isinstance(numeric_loglevel, int):
		raise ValueError('Invalid log level: %s' % log)
	logging.basicConfig(filename = 'log_run.log', level = numeric_loglevel, format = '%(asctime)s %(levelname)s: %(message)s')
	logging.info("run.py: " + str(args))
	#hRange = range(12,13)
	#vRange = range(10,11)
	#scriptFolder = '/home/scidb/scripts/MOD13Q1/'
	#period = 16
	#basebfilepath = '/home/scidb/'
	#hdf2binFolder = '/home/scidb/hdf2bin/'
	#loadFolder = '/home/scidb/toLoad/'
	#modisPath = '/home/scidb/MODIS_ARC/MODIS/MOD09Q1.005/' # '/dados1/modisOriginal/MOD13Q1/' # '/mnt/lun0/MODIS_ARC/MODIS/MOD09Q1.005/'
	#dates = buildDoy(2000, 2001, period)
	if modisFolderSchema == 'R-MODIS':
		loadhdfModisPackage(modisPath, basebfilepath, dates, hRange, vRange, hdf2binFolder, loadFolder, scriptFolder, lineMin, lineMax, sampMin, sampMax, period, prod, log)
	elif modisFolderSchema == 'MP-YEAR':
		loadhdfCHRONOS(modisPath, basebfilepath, dates, hRange, vRange, hdf2binFolder, loadFolder, scriptFolder, lineMin, lineMax, sampMin, sampMax, period, prod, log)
	#Use HSD folder structure of R MODIS PACKAGE. Each HDF to a binary file
	#loadhdfGISOBAMAsingle(modisPath, basebfilepath, dates, hRange, vRange, hdf2binFolder, loadFolder, scriptFolder, lineMin, lineMax, sampMin, sampMax, period)
	t1 = datetime.datetime.now()	
	tt = t1 - t0
	logging.info("Finished in " + str(tt))
	

if __name__ == "__main__":
   main(sys.argv[1:])
