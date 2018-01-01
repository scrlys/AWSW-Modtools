import sys

from ctypes import *
import time
import os
import shutil
import os.path


print(os.getcwd())


class PyCallback():
	Query = 0
	Unsub = 1
	Download = 2
	Info = 3
	

class WorkshopItem(Structure):
	_fields_ = [("itemID", c_longlong),
				("state", c_uint),
				("filepath", c_char * 256)]
				
class InfoStruct(Structure):
	_fields_ = [("num", c_uint), ("wsiarr", POINTER(WorkshopItem))]

class WorkshopData(Structure):
	_fields_ = [("m_nPublishedFileId", c_longlong),
				("m_eResult", c_int),
				("m_eFileType", c_int),
				("m_nCreatorAppID", c_int),
				("m_nConsumerAppID", c_int),
				("m_rgchTitle", c_char * 129),
				("m_rgchDescription", c_char * 8000),
				("m_ulSteamIDOwner", c_longlong),
				("m_rtimeCreated", c_uint),
				("m_rtimeUpdated", c_uint),
				("m_rtimeAddedToUserList", c_uint),
				("m_eVisibility", c_int),
				("m_bBanned", c_bool),
				("m_bAcceptedForUse", c_bool),
				("m_bTagsTruncated", c_bool),
				("m_rgchTags", c_char * 1025),
				("m_hFile", c_longlong),
				("m_hPreviewFile", c_longlong),
				("m_pchFileName", c_char * 260),
				("m_nFileSize", c_uint),
				("m_nPreviewFileSize", c_uint),
				("m_rgchURL", c_char * 256),
				("m_unVotesUp", c_uint),
				("m_unVotesDown", c_uint),
				("m_flScore", c_float),
				("m_unNumChildren", c_uint),
				("m_pchPreviewLink", c_char * 256)]

CB_QUERY = CFUNCTYPE(None, POINTER(WorkshopData), c_uint)
CB_UNSUB = CFUNCTYPE(None, c_longlong)
CB_DL = CFUNCTYPE(None, POINTER(WorkshopItem))
CB_INFO = CFUNCTYPE(None, POINTER(WorkshopItem), c_uint)


class SteamMgr():
	def __init__(self):
		self.Callbacks = {}
		
		self.Callbacks[PyCallback.Query] = []
		self.Callbacks[PyCallback.Unsub] = []
		self.Callbacks[PyCallback.Download] = []
		self.Callbacks[PyCallback.Info] = []
		
		steamlib = CDLL(os.path.join(os.getcwd(), 'AWSWSteam.dll'))
		#self.Test2 = steamlib.HandleException
		self.InitSteam = steamlib.InitSteam
		self.InitSteam.restype = c_bool
		
		self.c_user_func = steamlib.GetPersona
		self.c_user_func.argtypes = [c_longlong]
		self.c_user_func.restype = c_char_p

		# Don't expose this
		register_cb = steamlib.RegisterCallback
		register_cb.restype = None
		
		self.CleanItems = steamlib.CleanItems
		
		self.InitSuccess = self.InitSteam()
		if self.InitSuccess:
			print("SteamAPI Init successful.")
		
		def info_callback(info, arr_len):
			for cb in self.Callbacks[PyCallback.Info]:
				cb(info, arr_len)
		
			print(arr_len)
			print(info[0].itemID)
			print(info[1].filepath)
			print(info[1].itemID)
				
		def unsubscribe_callback(mod_id):
			for cb in self.Callbacks[PyCallback.Unsub]:
				cb(mod_id)
		
			print("We got dis : {}".format(mod_id))
			
		def download_callback(info):
			for cb in self.Callbacks[PyCallback.Download]:
				cb(info)
		
			print(info[0].filepath)
			
		def query_callback(array, arr_len):
			for cb in self.Callbacks[PyCallback.Query]:
				cb(array, arr_len)
				
			print("Got CB")
			#print("Title idx 0: {}".format(array[49].m_rgchTitle))
			#print("Array sz: {}".format(arr_len))
			#print("PreviewLink idx 0: {}".format(array[49].m_pchPreviewLink))
			
		self.info_callback = info_callback
		self.unsubscribe_callback = unsubscribe_callback
		self.download_callback = download_callback
		self.query_callback = query_callback
		
		self.c_query_func = CB_QUERY(self.query_callback)
		self.c_unsub_func = CB_UNSUB(self.unsubscribe_callback)
		self.c_dl_func = CB_DL(self.download_callback)
		self.c_info_func = CB_INFO(self.info_callback)
		
		

		register_cb(self.c_query_func, PyCallback.Query)
		register_cb(self.c_unsub_func, PyCallback.Unsub)
		register_cb(self.c_dl_func, PyCallback.Download)
		register_cb(self.c_info_func, PyCallback.Info)
		
		steamlib.GetItems.restype = POINTER(InfoStruct)
		self.GetItems_int = steamlib.GetItems
		
		self.CleanItems = steamlib.CleanItems

		self.QueryApi = steamlib.QueryApi
		#self.QueryApi(1)
		
		self.DownloadItem = steamlib.DownloadItem
		self.DownloadItem.argtypes = [c_ulonglong]
		self.DownloadItem.restype = c_bool
		
		self.Unsubscribe = steamlib.Unsubscribe
		self.Subscribe = steamlib.Subscribe
		
	def register_callback(self, type, func):
		self.Callbacks[type].append(func)
		
	def unregister_callback(self, type, func):
		self.Callbacks[type].remove(func)
			
			
	def GetItems(self):
		itemstruct = self.GetItems_int()
		if itemstruct[0].num == 0:
			self.CleanItems(itemstruct)
			return []
			
		ret = []
		
		print(itemstruct[0].wsiarr[1])
		for x in range(0, itemstruct[0].num):
			temp = {
				"itemID":int(itemstruct[0].wsiarr[x].itemID),
				"state":int(itemstruct[0].wsiarr[x].state),
				"filepath":str(itemstruct[0].wsiarr[x].filepath)
			}
			ret.append(temp)
		
		self.CleanItems(itemstruct)
		return ret

	def GetAllItems(self):
		# It seems the only way the callback can access these variables is through global variables
		# Be careful!
		global _result
		global _complete
		_result = None
		_complete = False
		
		def cb(array, arr_len):
			global _result
			global _complete
			_result = []
			if arr_len == 51:
				print("Null")
				return
			
			for x in range(arr_len):
				item = array[x]
				_result.append((item.m_nPublishedFileId, item.m_rgchTitle, self.GetPersona(item.m_ulSteamIDOwner), item.m_rgchDescription, item.m_pchPreviewLink))
				print(_result)
				
			
			_complete = True
				
		self.register_callback(PyCallback.Query, cb)
		
		self.QueryApi(1)
		
		# Block
		while not _complete:
			pass
			
		self.unregister_callback(PyCallback.Query, cb)
		
		return _result
	
	def GetItemFromID(self, id):
		# TODO: Don't look up all mods again
		for item in self.GetAllItems():
			if item[0] == id:
				return item
		return None
		
		
		
	def GetPersona(self, id):
		return self.c_user_func(id)
		
		
def get_instance():
	print(os.getcwd())
	global _instance
	try:
		return _instance
	except:
		_instance = SteamMgr()
		return _instance

#gSteamMgr = SteamMgr()

#print(gSteamMgr.GetItemFromID(946289437))