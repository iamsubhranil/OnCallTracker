from itertools import cycle
from datetime import datetime
import pickle
from threading import Thread, Event

PERSONS = ["Bernice", "Jose", "Karen", "Karina", "Luis", "Ricardo"]
PERSON_COUNT = len(PERSONS)
DEFAULT_FILENAME = "oncall.state"

# default date format
def dt(date):
    return date.strftime("%a %d %b, %I:%M:%S %p")

# default timedelta format
def td(timedelta):
    s = timedelta.seconds
    hours, remainder = divmod(s, 3600)
    minutes, seconds = divmod(remainder, 60)
    s = ""
    if hours > 0:
        s = " {:02}h".format(int(hours))
    if minutes > 0:
        s += " {:02}m".format(int(minutes))
    if seconds > 0:
        s += " {:02}s".format(int(seconds))
    return s

class Assignment:

    def __init__(self):
        self.last_assigned = -1
        self.assign_counter = [0] * PERSON_COUNT
        self.total_assignment = 0

    def assign(self, num=1):
        self.total_assignment += num
        assigned_to = {}
        minimum, remaining = divmod(num, 5)
        if minimum > 0:
            # everybody will get this many tasks at minimum
            for i in range(PERSON_COUNT):
                self.assign_counter[i] += minimum
                assigned_to[PERSONS[i]] = minimum
        if remaining > 0:
            for _ in range(remaining):
                self.last_assigned = (self.last_assigned + 1) % PERSON_COUNT
                self.assign_counter[self.last_assigned] += 1
                who = PERSONS[self.last_assigned]
                if who not in assigned_to:
                    assigned_to[who] = 1
                else:
                    assigned_to[who] += 1
        return assigned_to

class Logger:

    def __init__(self):
        self.logs = ""

    def log(self, *args):
        self.logs += "\n [" + dt(datetime.now()) + "] "
        for a in args:
            self.logs += str(a) + " "

    def info(self, *args):
        self.log("[Info]", *args)

    def error(self, *args):
        self.log("[Error]", *args)

    def warning(self, *args):
        self.log("[Warning]", *args)

class Session:

    def __init__(self, id_):
        self.catalog_assignment = Assignment()
        self.incident_assignment = Assignment()
        self.breaks = []
        self.ended = False
        self.break_started = False
        self.started_at = datetime.now()
        self.ended_at = None
        self.logger = Logger()
        self.logger.info("Session Started")
        self.id_ = id_

    def assign_catalog(self, count=1):
        if self.break_started:
            self.end_break()
        assignments = self.catalog_assignment.assign(count)
        self.logger.log("[CAT]", count, assignments)
        return assignments

    def assign_incident(self, count=1):
        if self.break_started:
            self.end_break()
        assignments = self.incident_assignment.assign(count)
        self.logger.log("[INC]", count, assignments)
        return assignments

    def start_break(self):
        self.break_started = True
        self.logger.info("Break Started")
        self.breaks.append([datetime.now(), None])

    def end_break(self):
        self.break_started = False
        self.logger.info("Break Ended")
        self.breaks[-1][1] = datetime.now()

    def end(self):
        self.ended = True
        self.ended_at = datetime.now()
        self.logger.info("Session Ended")

class State:

    def __init__(self):
        self.sessions = []
        self.active_session = None
        self.active_session_id = -1

    def get_active_session(self):
        return self.active_session

    def create_session(self):
        self.sessions.append(Session(len(self.sessions) + 1))
        self.active_session = self.sessions[-1]
        self.active_session_id = self.active_session.id_
        return self.active_session

    def set_active_session(self, idx):
        self.active_session_id = idx
        self.active_session = self.sessions[self.active_session_id]
        return self.active_session

    def copy(self, other):
        self.sessions = other.sessions
        self.active_session = other.active_session
        self.active_session_id = other.active_session_id

# handlers

def handle_new(args, state):
    if state.get_active_session() != None and \
        state.get_active_session().ended == False:
        state.get_active_session().end()
    state.create_session()
    print("New session created!")
    return True

def handle_inc(args, state):
    count = 1
    if len(args) == 2:
        try:
            count = int(args[1])
            if count < 0:
                raise ValueError("Positive value is required!")
        except:
            print("Invalid count passed!")
            return True
    assignments = state.get_active_session().assign_incident(count)
    print("Incident Assignments: ")
    for k in assignments:
        print(k + ":", assignments[k])
    return True

def handle_cat(args, state):
    count = 1
    if len(args) == 2:
        try:
            count = int(args[1])
            if count < 0:
                raise ValueError("Positive value is required!")
        except:
            print("Invalid count passed!")
            return True
    assignments = state.get_active_session().assign_catalog(count)
    print("Catalog Assignments:")
    for k in assignments:
        print(k + ":", assignments[k])
    return True

def handle_break(args, state):
    session = state.get_active_session()
    if session.break_started:
        print("Break ended!")
        session.end_break()
    else:
        print("Break started!")
        session.start_break()
    return True

def handle_end(args, state):
    session = state.get_active_session()
    session.end()
    print("Current session ended!")
    return True

def handle_exit(args, state):
    return False

def handle_session(args, state):
    if len(args) == 2:
        if args[1] == "list":
            for session in state.sessions:
                if session == state.get_active_session():
                    print("* ", end='')
                print("Session:", session.id_)
            return True
        else:
            try:
                switch = int(args[1]) - 1
                if switch > -1 and switch < len(state.sessions):
                    state.set_active_session(switch)
                    print("[Info] Active session set to: Session", state.get_active_session().id_)
                else:
                    print("[Error] Invalid session specified!")
                return True
            except:
                print("[Error] Invalid session specified!")
                return True
    else:
        session = state.get_active_session()
        if session.ended_at != None:
            print("Session timing:", dt(session.started_at), "-", dt(session.ended_at),
                "[", td(session.ended_at - session.started_at), "]")
        else:
            print("Session started at: ", dt(session.started_at), "[",
                  td(datetime.now() - session.started_at), "ago]")

        print("\nCatalog tasks:", session.catalog_assignment.total_assignment)
        if session.catalog_assignment.total_assignment > 0:
            print("Details:")
            for i, count in enumerate(session.catalog_assignment.assign_counter):
                print(PERSONS[i], "->", count)
            print("Last assignee:", PERSONS[session.catalog_assignment.last_assigned])

        print("\nIncident tasks:", session.incident_assignment.total_assignment)
        if session.incident_assignment.total_assignment > 0:
            print("Details:")
            for i, count in enumerate(session.incident_assignment.assign_counter):
                print(PERSONS[i], "->", count)
            print("Last assignee:", PERSONS[session.incident_assignment.last_assigned])

        print("\nBreaks taken:", len(session.breaks))
        if len(session.breaks) > 0:
            print("\nBreak details:")
            for i, b in enumerate(session.breaks):
                print(i + 1, " -> ", dt(b[0]), "-", end=' ')
                if b[1] != None:
                    print(dt(b[1]), "[", td(b[1] - b[0]), "]")
                else:
                    print()
        return True

def handle_log(args, state):
    if len(args) == 2:
        state.get_active_session().logger.log(args[1])
    else:
        print(state.get_active_session().logger.logs)
    return True

def handle_save(args, state, silent=False):
    filename = DEFAULT_FILENAME
    if len(args) == 2:
        filename = args[1]
    try:
        with open(filename, "wb") as f:
            pickle.dump(state, f)
        if not silent:
            print("[Info] Saved to:", filename)
        else:
            return None, True
    except Exception as e:
        if silent:
            return e, False
        else:
            print("[Error] The following error occurred:", e)
    return True

def handle_load(args, state):
    filename = DEFAULT_FILENAME
    if len(args) == 2:
        filename = args[1]
    try:
        with open(filename, "rb") as f:
            new_state = pickle.load(f)
            state.copy(new_state)
        print("[Info] Loaded from:", filename)
    except Exception as e:
        print("[Error] The following error occurred:", e)
    return True

def handle_help(args, state):
    print("""
        new -> Starts a new on call session
        inc [<x>] -> Assigns x new incident tasks
        cat [<x>] -> Assigns x new catalog tasks
        break -> Starts/stops a break session
        end -> Ends the current on call session
        exit -> Exits the repl
        session [list]/[<x>] -> Switches between sessions
        log [<message>] -> Views/adds to current session log
        save [<filename>] -> Saves state to a file (default: oncall.state)
        load [<filename>] -> Loads state from file (default: oncall.state)
        help -> Shows this help
        """)
    return True

def save_action(state, stop_event):
    while not stop_event.is_set():
        # save every 60seconds
        stop_event.wait(60)
        ex, success = handle_save([], state, True)
        if not success:
            print("[Error] Automatic save failed due to the following error:")
            print(ex)
            print("[Error] Manually run 'save' before exiting!")
            return

def repl():
    run = True
    state = State()
    handle_load([], state)
    stop_event = Event()
    save_thread = Thread(target=save_action, args=(state, stop_event))
    save_thread.start()
    while run:
        print(">> ", end='')
        commands = {"new": handle_new, "inc": handle_inc, "cat": handle_cat,
                    "break": handle_break, "end": handle_end,
                    "exit": handle_exit, "session": handle_session,
                    "log": handle_log, "save": handle_save,
                    "load": handle_load, "help": handle_help}
        try:
            input_arg = input().split(" ")
        except KeyboardInterrupt:
            run = False
            continue
        given = input_arg[0]
        if given not in commands:
            print("[Error] Invalid command given! Use one of:", *[x for x in commands])
            continue
        run = commands[given](input_arg, state)
    stop_event.set()
    save_thread.join()
    print("Exiting..")

if __name__ == "__main__":
    repl()
