from typing import List, Optional, Any, Union
from pydantic import BaseModel
from requests.auth import HTTPBasicAuth
import requests
import urllib3
import datetime
from enum import IntEnum
from loguru import logger
import numpy as np
from abb_robot_client.rws import ABBException, JointTarget, RobTarget
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class RAPIDExecutionState(BaseModel):
    ctrlexecstate: Any
    cycle: Any

class EventLogEntry(BaseModel):
    seqnum: int
    msgtype: int
    code: int
    tstamp: datetime.datetime
    args: List[Any]
    title: str
    desc: str
    conseqs: str
    causes: str
    actions: str

class EventLogEntryEvent(BaseModel):
    seqnum: int

class TaskState(BaseModel):
    name: str
    type: str
    taskstate: str
    excstate: str
    active: bool
    motiontask: bool

class RobAx(BaseModel):
    rax_1: float
    rax_2: float
    rax_3: float
    rax_4: float
    rax_5: float
    rax_6: float
    
class ExtAx(BaseModel):
    eax_a: float
    eax_b: float
    eax_c: float
    eax_d: float
    eax_e: float
    eax_f: float
    
class IpcMessage(BaseModel):
    data: str
    userdef: str
    msgtype: str
    cmd: str
    queue_name: str

class Signal(BaseModel):
    name: str
    lvalue: str

class ControllerState(BaseModel):
    state: str

class OperationalMode(BaseModel):
    mode: str

class VariableValue(BaseModel):
    name: str
    value: str
    task: Optional[str] = None

class SubscriptionResourceType(IntEnum):
    """Enum to select resource to subscribe. See :meth:`.RWS.subscribe()`"""
    ControllerState = 1
    """Subscribe to controller state resource"""
    OperationalMode = 2
    """Subsribe to operational mode resource"""
    ExecutionState = 3
    """Subscribe to executio state resource"""
    PersVar = 4
    """Subscribe to RAPID pers variable resource"""
    IpcQueue = 5
    """Subscribe to IPC queue resource"""
    Elog = 6
    """Subscribe to Event Log resource"""
    Signal = 7
    """Subscribe to signal resource"""

class SubscriptionResourcePriority(IntEnum):
    """Priority of subscribed resource. Only Signal and PersVar support high priority. See :meth:`.RWS.subscribe()`"""
    Low = 0
    Medium = 1
    High = 2

class SubscriptionResourceRequest(BaseModel):
    resource_type: SubscriptionResourceType
    priority: SubscriptionResourcePriority
    param: Any = None
    
class RWS2:
    """
    Robot Web Services 2.0 synchronous client. This class uses ABB Robot Web Services HTTP REST interface to interact
    with robot controller. Subscriptions can be created to provide streaming information. See the ABB
    documentation for more information: https://developercenter.robotstudio.com/api/RWS

    :param base_url: Base URL of the robot. For Robot Studio instances, this should be https://127.0.0.1:80,
                     the default value. For a real robot, 127.0.0.1 should be replaced with the IP address
                     of the robot controller. The WAN port ethernet must be used, not the maintenance port.
    :param username: The HTTPS username for the robot. Defaults to 'Default User'
    :param password: The HTTPS password for the robot. Defaults to 'robotics'
    """
    def __init__(self, base_url: str='https://127.0.0.1:80', username: str="Default User", password: str="robotics"):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.auth = HTTPBasicAuth(username, password)
        self._session = requests.Session()
        self._rmmp_session = None
        self._rmmp_session_t = None
        self.header = {"accept": "application/hal+json;v=2.0",
                       "Content-Type": "application/x-www-form-urlencoded;v=2.0"}
        self._session.verify = False


    def _do_get(self, relative_url: str, params=None):
        url = f"{self.base_url}/{relative_url}"
        try:
            response = self._session.get(url, headers=self.header, auth=self.auth, params=params, verify=self._session.verify)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error occurred: {e}")
            return None

    def _do_get_raw(self, relative_url: str, params=None):
        url = f"{self.base_url}/{relative_url}"
        response = self._session.get(url, headers=self.header, auth=self.auth, params=params, verify=self._session.verify)
        return response
    
    def _do_post(self, relative_url: str, data=None):
        url = f"{self.base_url}/{relative_url}"
        headers = self.header.copy()
        headers["Content-Type"] = "application/x-www-form-urlencoded;v=2.0"
        #TODO add response.e.code == -1073445859 to check for mastership error
        try:
            response = self._session.post(url, headers=headers, auth=self.auth, data=data if data is not None else "", verify=self._session.verify)
            response.raise_for_status()
            return response.json() if response.content else None
        except requests.RequestException as e:
            if response.status_code == 403:
                logger.error("Mastership required for this operation")
                raise ABBException("Mastership required for this operation", 403)
            print(f"Error occurred: {e}")
            return None
        
    def _do_post_raw(self, relative_url: str, data=None):
        url = f"{self.base_url}/{relative_url}"
        headers = self.header.copy()
        response = self._session.post(url, headers=headers, auth=self.auth, data=data if data is not None else "", verify=self._session.verify)

        return response
    
    def start(self, cycle: Optional[str] = 'asis', tasks: Optional[list[str]] = ["T_ROB1"]): #TODO
        """
        Start one or more RAPID tasks

        :param cycle: The cycle mode of the robot. Can be `asis`, `once`, or `forever`.
        :param tasks: One or more tasks to start.
        """

        rob_tasks = self.get_tasks()
        for t in tasks:
            if t not in rob_tasks:
                raise Exception(f"Cannot start unknown task {t}")

        for rob_task in rob_tasks.values():
            if not rob_task.motiontask:
                continue
            if rob_task.name in tasks:
                if not rob_task.active:
                    self.activate_task(rob_task.name)
            else:
                if rob_task.active:
                    self.deactivate_task(rob_task.name)

        payload={"regain": "continue", "execmode": "continue", "cycle": cycle, "condition": "none", "stopatbp": "disabled", "alltaskbytsp": "true"}
        res=self._do_post("rw/rapid/execution/start?mastership=implicit", payload)

    def activate_task(self, task: str):
        """
        Activate a RAPID task

        :param task: The name of the task to activate
        """
        self._do_post("rw/rapid/tasks/activate?mastership=implicit", data={"task": task})

    def deactivate_task(self, task: str) -> None:
        """
        Deactivate a RAPID task

        :param task: The name of the task to deactivate
        """
        self._do_post(f"rw/rapid/tasks/{task}/deactivate?mastership=implicit", data={"task": task})

    def stop(self):
        """
        Stop RAPID execution of normal tasks
        """
        payload={"stopmode": "stop"}
        res=self._do_post("rw/rapid/execution/stop?mastership=implicit", payload)

    def resetpp(self):
        """
        Reset RAPID program pointer to main in normal tasks
        """
        res=self._do_post("rw/rapid/execution/resetpp?mastership=implicit")
        
    def get_ramdisk_path(self) -> str:
        """
        Get the path of the RAMDISK variable on the controller

        :return: The RAMDISK path
        """
        res_json = self._do_get("ctrl/$RAMDISK")
        return res_json["state"][0]["value"]

    def get_execution_state(self) -> RAPIDExecutionState:
        """
        Get the RAPID execution state

        :return: The RAPID execution state
        """
        res_json = self._do_get("rw/rapid/execution")
        state = res_json["state"][0]
        return RAPIDExecutionState.model_validate({"ctrlexecstate": state["ctrlexecstate"], "cycle": state["cycle"]})
    
    def get_controller_state(self) -> str:
        """
        Get the controller state. The controller state can have the following values:

        `init`, `motoroff`, `motoron`, `guardstop`, `emergencystop`, `emergencystopreset`, `sysfail`

        RAPID can only be executed and the robot can only be moved in the `motoron` state.

        :return: The controller state
        """
        res_json = self._do_get("rw/panel/ctrl-state")
        state = res_json["state"][0]
        return state['ctrlstate']

    def set_controller_state(self, ctrl_state): 
        """Possible ctrl-states to set are `motoroff` or `motoron`"""
        payload = {"ctrl-state": ctrl_state}
        res=self._do_post("rw/panel/ctrl-state?mastership=implicit", payload)
        
    def set_motors_on(self):
        """
        Set the controller state to `motoron`
        """
        self.set_controller_state("motoron")
        
    def set_motors_off(self):
        """
        Set the controller state to `motoroff`
        """
        self.set_controller_state("motoroff")
    
    def get_operation_mode(self) -> str:
        """
        Get the controller operational mode. The controller operational mode can have the following values:

        `INIT`, `AUTO_CH`, `MANF_CH`, `MANR`, `MANF`, `AUTO`, `UNDEF`

        Typical values returned by the controller are `AUTO` for auto mode, and `MANR` for manual reduced-speed mode.
        
        :return: The controller operational mode.
        """
        res_json = self._do_get("rw/panel/opmode")        
        state = res_json["state"][0]
        return state["opmode"]
    
    def get_io(self, signal: str, network: str='', unit: str=''):
        """
        Get the value of an IO signal.

        :param signal: The name of the signal
        :param network: The network the signal is on. If the Network is <none> leave default value ''.
        :param unit: The device unit of the signal. If the device is <none> leave default value ''.
        :return: The value of the signal. Typically 1 for ON and 0 for OFF
        """
        if network and unit:
            res_json = self._do_get(f"rw/iosystem/signals/{network}/{unit}/{signal}")
        else: #TODO check for only network?
            res_json = self._do_get(f"rw/iosystem/signals/{signal}")
        value = res_json["_embedded"]["resources"][0]["lvalue"]
        return value
    
    def get_digital_io(self, signal: str, network: str='', unit: str='') -> int:
        """
        Get the value of a digital IO signal.

        :param signal: The name of the signal
        :param network: The network the signal is on. If the Network is <none> leave default value ''.
        :param unit: The device unit of the signal. If the device is <none> leave default value ''.
        :return: The value of the signal. Typically 1 for ON and 0 for OFF
        """
        value = self.get_io(signal, network, unit)
        return int(value)
    
    def set_digital_io(self, signal: str, value: bool|int, network: str='Local', unit: str='DRV_1'):
        """
        Set the value of an digital IO signal.

        :param value: The value of the signal. Bool or bool convertible input
        :param signal: The name of the signal
        :param network: The network the signal is on. The default `Local` will work for most signals.
        :param unit: The drive unit of the signal. The default `DRV_1` will work for most signals.
        """
        lvalue = '1' if bool(value) else '0'
        payload={'lvalue': lvalue}
        res=self._do_post(f"rw/iosystem/signals/{network}/{unit}/{signal}?mastership=implicit", payload)

    def get_analog_io(self, signal: str, network: str='Local', unit: str='DRV_1') -> float:
        """
        Get the value of an analog IO signal.

        :param signal: The name of the signal
        :param network: The network the signal is on. The default `Local` will work for most signals.
        :param unit: The drive unit of the signal. The default `DRV_1` will work for most signals.
        :return: The value of the signal
        """
        value = self.get_io(signal, network, unit)
        return float(value)
    
    # def set_analog_io(self, signal: str, value: Union[int,float], network: str='Local', unit: str='DRV_1'):
    #     """
    #     Set the value of an analog IO signal.

    #     :param value: The value of the signal
    #     :param signal: The name of the signal
    #     :param network: The network the signal is on. The default `Local` will work for most signals.
    #     :param unit: The drive unit of the signal. The default `DRV_1` will work for most signals.
    #     """
    #     payload={"mode": "value",'lvalue': value}
    #     res=self._do_post("rw/iosystem/signals/" + network + "/" + unit + "/" + signal + "?action=set", payload)
    
    # def get_rapid_variables(self, task: str="T_ROB1") -> List[str]:
    #     """
    #     Get a list of the persistent variables in a task

    #     :param task: The RAPID task to query
    #     :return: List of persistent variables in task
    #     """
    #     payload={
    #         "view": "block",
    #         "vartyp": "any",
    #         "blockurl": f"RAPID/{task}" if task is not None else "RAPID",
    #         "symtyp": "per",
    #         "recursive": "true",
    #         "skipshared": "FALSE",
    #         "onlyused": "FALSE",
    #         "stack": "0",
    #         "posl": "0",
    #         "posc": "0"
    #     }
    #     res_json = self._do_post(f"rw/rapid/symbols?action=search-symbols", payload)
    #     state = res_json["_embedded"]["_state"]
    #     return state

    def get_rapid_variable(self, var: str, task: str = "T_ROB1") -> str:
        """
        Get value of a RAPID pers variable

        :param var: The pers variable name
        :param task: The task containing the pers variable
        :return: The pers variable encoded as a string
        """
        res_json = self._do_get(f"rw/rapid/symbol/RAPID/{task}/{var}/data?mastership=implicit")
        state = res_json["state"][0]["value"]
        return state

    def set_rapid_variable(self, var: str, value: str, task: str = "T_ROB1"):
        """
        Set value of a RAPID pers variable

        :param var: The pers variable name
        :param value: The new variable value encoded as a string
        :param task: The task containing the pers variable
        """
        payload={'value': value}
        if task is not None:
            var1 = f"{task}/{var}"
        else:
            var1 = var
        self.request_mastership()
        res=self._do_post(f"rw/rapid/symbol/RAPID/{var1}/data?mastership=implicit", payload)
        self.release_mastership()
        
    def read_file(self, filename: str, directory: str = "$HOME") -> bytes:
        """
        Read a file off the controller

        :param filename: The relative path to the filename to read, e.g.: $HOME/...
        :param directory: The directory to read the file from, e.g. $HOME
        :return: The file bytes
        """
        res_json = self._do_get_raw(f"fileservice/{directory}/{filename}")

        contents = res_json.content
        return contents
    
    def read_file_str(self, filename: str, directory: str = "$HOME") -> str:
        res_bytes = self.read_file(filename, directory)
        return res_bytes.decode('utf-8')

    def upload_file(self, filename: str, contents: str, directory: str = "$HOME") -> None:
        """
        Upload a file to the controller

        :param filename: The filename to write
        :param contents: The file content as str
        :param directory: The directory to write the file to, e.g. $HOME
        """
        url=f"{self.base_url}/fileservice/{directory}/{filename}"
        header = {"Content-Type": "text/plain;v=2.0"}
        res=self._session.put(url, contents, auth=self.auth, headers=header)
        if not res.ok:
            raise Exception(res.reason)
        res.close()

    def delete_file(self, filename: str, directory: str = "$HOME") -> None:
        """
        Delete a file on the controller

        :param filename: The filename to delete
        """
        url=f"{self.base_url}/fileservice/{directory}/{filename}"
        res=self._session.delete(url, auth=self.auth, headers=self.header)
        res.close()
    
    # def list_files(self, path: str) -> List[str]:
    #     """
    #     List files at a path on a controller

    #     :param path: The path to list
    #     :return: The filenames in the path
    #     """
    #     res_json = self._do_get(f"fileservice/{path}")
    #     state = res_json["_embedded"]["_state"]
    #     return [f["_title"] for f in state]

    def read_event_log(self, elog: int=0) -> List[EventLogEntry]:
        """
        Read the controller event log

        :param elog: The event log id to read
        :return: The event log entries        
        """
        o=[]
        res_json = self._do_get("rw/elog/" + str(elog) + "/?lang=en")
        log = res_json["_embedded"]["resources"]
        
        for log_entry in log:
            entry_dict = {
                "seqnum": int(log_entry["_title"].split("/")[-1]),
                "msgtype": int(log_entry["msgtype"]),
                "code": int(log_entry["code"]),
                "tstamp": datetime.datetime.strptime(log_entry["tstamp"], '%Y-%m-%d T %H:%M:%S'),
                "title": log_entry["title"],
                "desc": log_entry["desc"],
                "conseqs": log_entry["conseqs"],
                "causes": log_entry["causes"],
                "actions": log_entry["actions"],
                "args": [],
            }
            nargs = int(log_entry["argc"])
            if "argv" in log_entry:
                for arg in log_entry["argv"]:
                    entry_dict["args"].append(arg["value"])
            o.append(EventLogEntry.model_validate(entry_dict))
            
        return o
    
    
    def get_tasks(self) -> dict[str, TaskState]:
        """
        Get controller tasks and task state

        :return: The tasks and task state
        """
        o = {}
        res_json = self._do_get("rw/rapid/tasks")
        if res_json is None:
            return o
        resources = res_json["_embedded"]["resources"]
        for s in resources:
            if "name" not in s:
                continue  # skip non-task resources
            try:
                o[s["name"]] = TaskState.model_validate(s)
            except Exception as e:
                print(f"Failed to parse task: {s.get('name', '<unknown>')}, error: {e}")
        return o
            
    def get_jointtarget(self, task: str = 'T_ROB1') -> JointTarget:
        """
        Get the current joint target of the specified task.

        :param task: The name of the task to get the joint target from.
        :return: The current joint target.
        """
        res_json = self._do_get(f"rw/rapid/tasks/{task}/motion/jointtarget")
        if res_json is None:
            raise Exception("Failed to get joint target")
        state_list = res_json.get("state", [])
        if not state_list:
            raise Exception("No joint target state found")

        joint_data = state_list[0]
        robjoint=np.array([joint_data["rax_1"], joint_data["rax_2"], joint_data["rax_3"], joint_data["rax_4"], joint_data["rax_5"], 
            joint_data["rax_6"]], dtype=np.float64)
        extjoint=np.array([joint_data["eax_a"], joint_data["eax_b"], joint_data["eax_c"], joint_data["eax_d"], joint_data["eax_e"], 
            joint_data["eax_f"]], dtype=np.float64)
        return JointTarget(robax=robjoint, extax=extjoint)

    
    def get_robtarget(self, mechunit='ROB_1', tool='tool0', wobj='wobj0', coordinate='Base') -> RobTarget:
        """
        Get the current robtarget (cartesian pose) for the specified mechunit

        :param mechunit: The mechanical unit to read
        :param tool: The tool to use to compute robtarget
        :param wobj: The wobj to use to compute robtarget
        :param coordinate: The coordinate system to use to compute robtarget. Can be `Base`, `World`, `Tool`, or `Wobj`
        :return: The current robtarget

        """
        res_json=self._do_get(f"rw/motionsystem/mechunits/{mechunit}/robtarget?tool={tool}&wobj={wobj}&coordinate={coordinate}")
        state = res_json["state"][0]
        trans=np.array([state["x"], state["y"], state["z"]], dtype=np.float64)
        rot=np.array([state["q1"], state["q2"], state["q3"], state["q4"]], dtype=np.float64)
        robconf=np.array([state["cf1"],state["cf4"],state["cf6"],state["cfx"]], dtype=np.float64)
        extax=np.array([state["eax_a"], state["eax_b"], state["eax_c"], state["eax_d"], state["eax_e"], 
            state["eax_f"]], dtype=np.float64)
        return RobTarget(trans,rot,robconf,extax)

    
    # def _rws_value_to_jointtarget(self, val):
    #     v1=re.match('^\\[\\[([^\\]]+)\\],\\[([^\\]]+)\\]',val)
    #     robax = np.deg2rad(np.fromstring(v1.groups()[0],sep=','))
    #     extax = np.deg2rad(np.fromstring(v1.groups()[1],sep=','))
    #     return JointTarget(robax,extax)
    
    # def _jointtarget_to_rws_value(self, val):
    #     if not np.shape(val[0]) == (6,):
    #         raise Exception("Invalid jointtarget")
    #     if not np.shape(val[1]) == (6,):
    #         raise Exception("Invalid jointtarget")
    #     robax=','.join([format(x, '.4f') for x in np.rad2deg(val[0])])
    #     extax=','.join([format(x, '.4f') for x in np.rad2deg(val[1])])
    #     rws_value="[[" + robax + "],[" + extax + "]]"
    #     return rws_value
    
    # def get_rapid_variable_jointtarget(self, var, task: str = "T_ROB1") -> JointTarget:
    #     """
    #     Get a RAPID pers variable and convert to JointTarget

    #     :param var: The pers variable name
    #     :param task: The task containing the pers variable
    #     :return: The pers variable encoded as a JointTarget
    #     """
    #     v = self.get_rapid_variable(var, task)
    #     return self._rws_value_to_jointtarget(v)
    
    # def set_rapid_variable_jointtarget(self,var: str, value: JointTarget, task: str = "T_ROB1"):
    #     """
    #     Set a RAPID pers variable from a JointTarget

    #     :param var: The pers variable name
    #     :param value: The new variable JointTarget value
    #     :param task: The task containing the pers variable
    #     """
    #     rws_value=self._jointtarget_to_rws_value(value)
    #     self.set_rapid_variable(var, rws_value, task)
            
    # def _rws_value_to_jointtarget_array(self,val):
    #     m1=re.match('^\\[(.*)\\]$',val)
    #     if len(m1.groups()[0])==0:
    #         return []
    #     arr=[]
    #     val1=m1.groups()[0]
    #     while len(val1) > 0:
    #         m2=re.match('^(\\[\\[[^\\]]+\\],\\[[^\\]]+\\]\\]),?(.*)$',val1)            
    #         val1 = m2.groups()[1]
    #         arr.append(self._rws_value_to_jointtarget(m2.groups()[0]))
        
    #     return arr       
    
    def get_rapid_variable_num(self, var: str, task: str = "T_ROB1") -> float:
        """
        Get a RAPID pers variable and convert to float

        :param var: The pers variable name
        :param task: The task containing the pers variable
        :return: The pers variable encoded as a float
        """
        return float(self.get_rapid_variable(var,task))
    
    def set_rapid_variable_num(self, var: str, val: float, task: str = "T_ROB1"):
        """
        Set a RAPID pers variable from a float

        :param var: The pers variable name
        :param value: The new variable float value
        :param task: The task containing the pers variable
        """
        self.set_rapid_variable(var, str(val), task)
        
    # def get_rapid_variable_num_array(self, var, task: str = "T_ROB1") -> np.ndarray:
    #     """
    #     Get a RAPID pers variable float array

    #     :param var: The pers variable name
    #     :param task: The task containing the pers variable
    #     :return: The variable value as an array
    #     """
    #     val1=self.get_rapid_variable(var,task)
    #     m=re.match("^\\[([^\\]]*)\\]$", val1)
    #     val2=m.groups()[0].strip()
    #     return np.fromstring(val2,sep=',')
    
    # def set_rapid_variable_num_array(self, var: str, val: List[float], task: str = "T_ROB1"):
    #     """
    #     Set a RAPID pers variable from a float list or array

    #     :param var: The pers variable name
    #     :param value: The new variable float array value
    #     :param task: The task containing the pers variable
    #     """
    #     self.set_rapid_variable(var, "[" + ','.join([str(s) for s in val]) + "]", task)
    
    def read_ipc_message(self, queue_name: str, timeout: float=0) -> List[IpcMessage]:
        """
        Read IPC message. IPC is used to communicate with RMQ in controller tasks. Create IPC using 
        try_create_ipc_queue().

        :param queue_name: The name of the queue created using try_create_ipc_queue()
        :param timeout: The timeout to receive a message in seconds
        :return: Messages received from IPC queue
        """
        o=[]
        
        res_json=self._do_get(f"rw/dipc/{queue_name}/{timeout}")
        for state in res_json["_embedded"]["_state"]:
            if not state["_type"] == "dipc-read-li":
                raise Exception("Invalid IPC message type")
            ipc_dict = {
                "data": state["dipc-data"],
                "userdef": state["dipc-userdef"],
                "msgtype": state["dipc-msgtype"],
                "cmd": state["dipc-cmd"],
                "queue_name": state["queue-name"]
            }

            o.append(IpcMessage.model_validate(ipc_dict))

            #o.append(RAPIDEventLogEntry(msg_type,code,tstamp,args,title,desc,conseqs,causes,actions))
        return o
    
    def get_speedratio(self) -> float:
        """
        Get the current speed ratio

        :return: The current speed ratio between 0% - 100%
        """
        res_json=self._do_get(f"rw/panel/speedratio")
        state = res_json["state"][0]
        if not state["_type"] == "pnl-speedratio":
            raise Exception("Invalid speedratio type")
        return float(state["speedratio"])
    
    def set_speedratio(self, speedratio: float):
        """
        Set the current speed ratio

        :param speedratio: The new speed ratio between 0% - 100%
        """
        payload = {"speed-ratio": str(speedratio)}
        self._do_post("rw/panel/speedratio?mastership=implicit", payload)
        
    
    # def send_ipc_message(self, target_queue: str, data: str, queue_name: str, cmd: int=111, userdef: int=1, msgtype: int=1 ):
    #     """
    #     Send an IPC message to the specified queue

    #     :param target_queue: The target IPC queue. Can also be the name of a task to send to RMQ of controller task.
    #     :param data: The data to send to the controller. Encoding must match the expected type of RMQ
    #     :param queue_name: The queue to send message from. Must be created with try_create_ipc_queue()
    #     :param cmd: The cmd entry in the message
    #     :param userdef: User defined value
    #     :param msgtype: The type of message. Must be 0 or 1
    #     """
    #     payload={"dipc-src-queue-name": queue_name, "dipc-cmd": str(cmd), "dipc-userdef": str(userdef), \
    #              "dipc-msgtype": str(msgtype), "dipc-data": data}
    #     res=self._do_post("rw/dipc/" + target_queue + "?action=dipc-send", payload)
    
    # def get_ipc_queue(self, queue_name: str) -> Any: #TODO TEST
    #     """
    #     Get the IPC queue

    #     :param queue_name: The name of the queue
    #     """
    #     res=self._do_get(f"rw/dipc/{queue_name}")
    #     return res
    
    # def try_create_ipc_queue(self, queue_name: str, queue_size: int=4440, max_msg_size: int=444) -> bool: #TODO TEST
    #     """
    #     Try creating an IPC queue. Returns True if the queue is created, False if queue already exists. Raises
    #     exception for all other errors.

    #     :param queue_name: The name of the new IPC queue
    #     :param queue_size: The buffer size of the queue
    #     :param max_msg_size: The maximum message size of the queue
    #     :return: True if queue created, False if queue already exists
        
    #     """
    #     try:
    #         payload={"dipc-queue-name": queue_name, "dipc-queue-size": str(queue_size), "dipc-max-msg-size": str(max_msg_size)}
    #         self._do_post("rw/dipc", payload)
    #         return True
    #     except ABBException as e:
    #         if e.code==-1073445879:
    #             return False
    #         raise
    
    # def request_rmmp(self, timeout: float=5):
    #     """
    #     Request Remote Mastering. Required to alter pers variables in manual control mode. The teach pendant
    #     will prompt to enable remote mastering, and the user must confirm. Once remote mastering is enabled,
    #     poll_rmmp() must be executed periodically to maintain rmmp.

    #     :param timeout: The request timeout in seconds
    #     """
    #     t1=time.time()
    #     self._do_post('users/rmmp?json=1', {'privilege': 'modify'})
    #     while time.time() - t1 < timeout:
            
    #         res_json=self._do_get('users/rmmp/poll?json=1')
    #         state = res_json["_embedded"]["_state"][0]
    #         if not state["_type"] == "user-rmmp-poll":
    #             raise Exception("Invalid rmmp poll type")
    #         status = state["status"]
    #         if status=="GRANTED":
    #             self.poll_rmmp()
    #             return
    #         elif status!="PENDING":
    #             raise Exception("User did not grant remote access")                               
    #         time.sleep(0.25)
    #     raise Exception("User did not grant remote access")
    
    # def poll_rmmp(self):
    #     """
    #     Poll rmmp to maintain remote mastering. Call periodically after rmmp enabled using request_rmmp()
    #     """
        
    #     # A "persistent session" can only make 400 calls before
    #     # being disconnected. Once this connection is lost,
    #     # the grant will be revoked. To work around this,
    #     # create parallel sessions with copied session cookies
    #     # to maintain the connection.
        
    #     url="/".join([self.base_url, 'users/rmmp/poll?json=1'])
        
    #     old_rmmp_session=None
    #     if self._rmmp_session is None:
    #         self._do_get(url)
    #         self._rmmp_session=requests.Session()
    #         self._rmmp_session_t=time.time()            
            
    #         for c in self._session.cookies:
    #             self._rmmp_session.cookies.set_cookie(c) 
    #     else:
    #         if time.time() - self._rmmp_session_t > 30:
    #             old_rmmp_session=self._rmmp_session
    #             rmmp_session=requests.Session()
                
    #             for c in self._session.cookies:
    #                 rmmp_session.cookies.set_cookie(c)
        
    #     rmmp_session=self._rmmp_session        
                
    #     res=rmmp_session.get(url, auth=self.auth)
    #     res_json=self._process_response(res)
    #     state = res_json["_embedded"]["_state"][0]
    #     if not state["_type"] == "user-rmmp-poll":
    #         raise Exception("Invalid rmmp poll type")
                
    #     if old_rmmp_session is not None:
    #         self._rmmp_session=rmmp_session
    #         self._rmmp_session_t=time.time()
    #         try:
    #             old_rmmp_session.close()
    #         except:
    #             pass
       
    #     return state["status"] == "GRANTED"
    
    
    
    
    
    
    
    ################ new #####################
    def request_mastership(self) -> None:
        """
        Request mastership for the client

        """
        response = self._session.post(f"{self.base_url}/rw/mastership/request", headers=self.header, auth=self.auth)
        
    def release_mastership(self) -> None:
        """
        Release mastership for the client
        """
        
        response = self._session.post(f"{self.base_url}/rw/mastership/release", headers=self.header, auth=self.auth)
        # if response.status_code == 403:
        #     logger.warning("Mastership request denied (403). Trying to release and re-request.")
        #     self._session.post(f"{self.base_url}/rw/mastership/release", headers=header, auth=self.auth)
        #     response = self._session.post(f"{self.base_url}/rw/mastership/request", data=data, headers=header, auth=self.auth)
        # if response.status_code == 204:
        #     logger.success("Mastership request granted")

        # else:
        #     logger.error(f"Failed to request mastership, status code: {response.status_code}")
        # return response
    
    
def test_RWS2():
    client = RWS2()
    # tasks = client.get_tasks()
    # jointtargets = client.get_jointtarget()
    # client.resetpp()
    # res = client.get_execution_state()

    # print("Execution State:", res)

if __name__ == "__main__":
    # test_rrc_robot_initialization()
    # test_RW7_rws()
    test_RWS2()
    