import logging
import winreg
import threading

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s,%(levelname)-5.5s [%(name)s] %(message)s', filename='watchRegistry.log')
log = logging.getLogger()

key = winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\RunAgain', 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)

class value_thread(threading.Thread):
    def __init__(self, main, winreg_id, value, key, winreg_type, stop_change):
        threading.Thread.__init__(self)
        self.main_thread = main
        self.winreg_id = winreg_id
        self.key = key
        self.value = value
        self.stopped = False
        self.winreg_type = winreg_type
        self.updating = False
        self.stop_change = stop_change

    def setUpdating(self, boolean):
        self.updating = boolean
        
    def setWinRegId(self, new_id):
        self.winreg_id = new_id
        
    def stop(self):
        self.stopped = True
    
    def isStopped(self):
        return self.stopped
    
    def getId(self):
        return self.winreg_id
    
    def getKey(self):
        return self.key
        
    def run(self):
        while True:
            if self.updating:
                continue
            if self.stopped:
                return
            # Try to retrieve the EnumValue, if it is None, it was deleted. So we need to stop the thread
            try:
                self.new_check = winreg.EnumValue(key, self.winreg_id)
                # Grab new values obtained from registry value check
                new_value = self.new_check[1]
                new_name = self.new_check[0]
                new_type = self.new_check[2]
                
                # Compare the current value with the new value
                if new_value != self.value:
                    # Log the change and set the value to the new value
                    log.info('Key: {} Value Changed From: {} To: {}'.format(self.key, self.value, new_value))
                    
                    if self.stop_change:
                        winreg.SetValueEx(key, self.key, 0, self.winreg_type, self.value)
                        print('Doing this')
                        continue
                    
                    self.value = new_value
                
                # Compare the current value with the new value
                if new_type != self.winreg_type:
                    # Log the change and set the value to the new value
                    log.info('Key: {} Type Changed From: {} To: {}'.format(self.key, self.winreg_type, new_type))
                    
                    if self.stop_change:
                        winreg.SetValueEx(key, self.key, 0, self.winreg_type, self.value)
                        print('Doing this')
                        continue
                    
                    self.winreg_type = new_type
                
                # Compare the current value with the new value
                if self.key != new_name:
                    # Log the change, notify the main thread of the change, and set the value to the new value
                    log.info('Key: {} Name Changed To: {}'.format(self.key, new_name))
                    
                    if self.stop_change:
                        winreg.SetValueEx(key, self.key, 0, self.winreg_type, self.value)
                        print('Doing this')
                        continue
                    
                    self.main_thread.update_name(self.key, new_name)
                    self.key = new_name
            except WindowsError as e:
                self.stopped = True
                return

class main_thread(threading.Thread):
    def __init__(self, initial_amount, stop_change):
        threading.Thread.__init__(self)
        self.amount = initial_amount
        self.threads = []
        self.stopped = False
        self.names = []
        self.stop_change = stop_change
        ead
        self.internal_start()
    
    ''' Start job that will grab and create all threads on start '''
    def internal_start(self):
        for i in range(winreg.QueryInfoKey(key)[1]):
            reg_value = winreg.EnumValue(key, i)
            reg_thread = value_thread(self, i, reg_value[1], reg_value[0], reg_value[2], self.stop_change)
            self.names.append(reg_value[0])
            self.threads.append(reg_thread)
            reg_thread.start()
    
    ''' Kill all threads and kill self '''
    def stop(self):
        self.stopped = True
        for x in self.threads:
            x.stop()
        self._join_threads()
    
    ''' Only called when hard-killing all threads '''
    def _join_threads(self):
        for x in self.threads:
            x.join()
            
    ''' Kill off and remove threads from overall thread list '''
    def _join_killed_threads(self):
        removed_threads = []
        for x in self.threads:
            if x.isStopped():
                removed_threads.append(x)
                x.join()
        for x in removed_threads:
            self.threads.remove(x)
    
    ''' Return a thread object based off of a key '''
    def get_thread_by_name(self, name):
        for x in self.threads:
            if x.getKey() == name:
                return x
        return None
    
    ''' Called by a thread to ensure names are updated '''
    def update_name(self, old, new):
        self.names.remove(old)
        self.names.append(new)
    
    ''' Ensure all threads have a proper id for checking the hive-key values '''
    def _update_ids(self):
        for i in range(winreg.QueryInfoKey(key)[1]):
            reg_value = winreg.EnumValue(key, i)
            reg_thread = self.get_thread_by_name(reg_value[0])
            if reg_thread.getId() != i:
                reg_thread.setWinRegId(i)
    
    ''' Turn on/off updating of threads '''
    def _update_threads(self, boolean):
        for x in self.threads:
            x.setUpdating(boolean)
    
    ''' Called on update of a size of value keys '''
    def check_names(self):
        # Performing batch update, turn on updating of threads so they don't call during this time
        self._update_threads(True)
        new_names = []
        reg_values = []
        
        # Grab all current values in key for comparison
        for i in range(winreg.QueryInfoKey(key)[1]):
            reg_value = winreg.EnumValue(key, i)
            new_names.append(reg_value[0])
            reg_values.append(reg_value)
        
        # Get all names that are no longer in the new name list
        removed_names = []
        for y in self.names:
            if y not in new_names:
                log.warning('Key Removed: {}'.format(y))
                removed_names.append(y)

        # Remove all names no longer needed from the names list.
        # This has to be called outside of the for y in self.names loop to not cause an error
        for lost_name in removed_names:
            self.names.remove(lost_name)
        
        # Start checking for new names
        for x in new_names:
            # If name is not in self.names, start the process of creating a new thread
            if x not in self.names:
                log.warning('Key Added: {}'.format(x))
                for reg_value in reg_values:
                    # Compare names so we know which one we are watching now
                    if x == reg_value[0]:
                        reg_thread = value_thread(self, -1, reg_value[1], reg_value[0], reg_value[2], self.stop_change)
                        # Ensure the thread is in updating mode so we can edit it still
                        reg_thread.setUpdating(True)
                        self.names.append(reg_value[0])
                        self.threads.append(reg_thread)
                        # Officially start the thread
                        reg_thread.start()
        
        # Change all IDs to fit where they are supposed to go
        self._update_ids()
        # Disable update stop on all threads
        self._update_threads(False)
        # Kill off any remaining threads that are stopped
        self._join_killed_threads()
    
    ''' Thread-needed function describing what the thread needs to do '''
    def run(self):
        while True:
            if self.stopped:
                return
            new_amount = winreg.QueryInfoKey(key)[1]
            if self.amount != new_amount:
                log.warning('Key Amount Changed From {} To {}'.format(self.amount, new_amount))
                self.amount = new_amount
                self.check_names()

if __name__ == '__main__':
    main = main_thread(winreg.QueryInfoKey(key)[1], True)
    main.start()
    while True:
        inp = input('Type \'Exit\' To Stop: ')
        if inp == 'Exit':
            main.stop()
            main.join()
            break
