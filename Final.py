import streamlit as st
import pandas as pd
import calendar
from datetime import datetime, timedelta
from peewee import *
import pygame
from time import sleep
from threading import Thread


sound = 'assets/alarm.wav'
if 'search_term' not in st.session_state:
    st.session_state.search_term = ""  # Initialize search term
if 'page' not in st.session_state:
    st.session_state.page = 'Login'  # Default to 'Login' page
if 'current_user' not in st.session_state:
    st.session_state.current_user = None  # Track logged-in user
if 'login_attempted' not in st.session_state:
    st.session_state.login_attempted = False  # Initialize to False if not set


# Function to switch between pages
def switch_page(page_name):
    st.session_state.page = page_name


# Database configuration
db = SqliteDatabase('task7.db')

# Define User and Task models
class User(Model):
    name = CharField(unique=True)
    password = CharField()

    class Meta:
        database = db

class Task(Model):
    task_name = CharField()
    due_date = DateField()
    time_estimate = IntegerField()
    time_due = TimeField()
    alarm_time = TimeField(null=True) 
    urgency = BooleanField()
    importance = BooleanField()
    done = BooleanField(default=False)
    notification_time = IntegerField(default=0)  # Notification in minutes before task
    alarm_enabled = BooleanField(default=False)
    alarm_triggered = BooleanField(default=False)
    user = ForeignKeyField(User, backref='tasks')

    class Meta:
        database = db

# Initialize the database
db.connect()
db.create_tables([User, Task], safe=True)


# Alert for due or overdue tasks
def check_notifications_and_alarm():
    if st.session_state.current_user:
        user_tasks = Task.select().where(Task.user == st.session_state.current_user)

        for task in user_tasks:
            # Combine due date and due time to get the full due datetime
            due_datetime = datetime.combine(task.due_date, task.time_due)
            
            # Calculate notification time: notify before `due_time`
            notification_datetime = due_datetime - timedelta(minutes=task.notification_time)
            
            current_time = datetime.now()

            # Check if it's time for a notification
            if current_time >= notification_datetime and current_time < due_datetime and not task.done:
                st.info(f"Reminder: Task '{task.task_name}' is due soon!")
            
            # Check if it's time for the alarm to trigger
            if current_time >= due_datetime and not task.alarm_triggered and not task.done and task.alarm_enabled:
                st.warning(f"ALARM! Task '{task.task_name}' is due now!")
                with open(sound, "rb") as alarm_file:
                    st.audio(alarm_file.read(), format="audio/wav")
                task.alarm_triggered = True
                task.save()






def play_alarm():
    """Function to play the alarm sound using Streamlit's native audio feature."""
    with open(sound, "rb") as alarm_file:
        st.audio(alarm_file.read(), format="audio/wav")
        


                    
def register_user():
    name = st.text_input("Enter your name", key="reg_name")
    password = st.text_input("Enter your password", type="password", key="reg_pass")
    if st.button("Register"):
        try:
            User.create(name=name, password=password)
            st.success("Registration successful!")
            st.session_state.current_user = User.get(User.name == name)
            st.session_state.page = 'Add Task'
        except IntegrityError:
            st.error("User already exists. Try a different name.")


def login_user():
    name = st.text_input("Enter your name", key="login_name")
    password = st.text_input("Enter your password", type="password", key="login_pass")
    if st.button("Login"):
        user = User.get_or_none(User.name == name, User.password == password)
        if user:
            st.success("Login successful!")
            st.session_state.current_user = user
            st.session_state.page = 'Add Task'
        else:
            st.error("Incorrect username or password.")


def logout_user():
    st.session_state.current_user = None
    st.session_state.page = 'Login'
    st.success("You have been logged out.")


def add_task():
    if st.session_state.current_user:
        st.subheader("Add Task")
        task_name = st.text_input("Enter task name")
        due_date = st.date_input("Enter due date", value=datetime.today().date())
        time_estimate = st.number_input("Time estimate (in minutes)", min_value=1)
        time_due = st.time_input("Select Time", value=datetime.now(), key = "time_due_input")
        set_alarm = st.checkbox("Set an alarm for this task")  
        urgency = st.selectbox("Is it urgent?", [False, True], format_func=lambda x: "Urgent" if x else "Not Urgent")
        importance = st.selectbox("Is it important?", [False, True], format_func=lambda x: "Important" if x else "Not Important")
        notification_time = st.number_input("Notification (minutes before due)", min_value=0)

        if st.button("Add Task", key="add_task_button"):
            Task.create(
                task_name=task_name,
                due_date=due_date,
                time_estimate=time_estimate,
                time_due = time_due,
                alarm_enabled = set_alarm,
                urgency=urgency,
                importance=importance,
                notification_time=notification_time,
                user=st.session_state.current_user.id
            )
            st.success(f"Task '{task_name}' added successfully!")


def view_tasks():
    st.subheader("Task Calendar")
    
    if st.session_state.current_user:
        user_tasks = Task.select().where(Task.user == st.session_state.current_user)
        
        if not user_tasks:
            st.warning("No tasks found.")
            return
        
        task_dates = [task.due_date for task in user_tasks]
        task_names = [task.task_name for task in user_tasks]
        task_time_estimate = [task.time_estimate for task in user_tasks]
        task_time_due = [task.time_due for task in user_tasks]
        
        # Month dropdown with month names
        months = [calendar.month_name[i] for i in range(1, 13)]  # List of month names
        month_name = st.selectbox("Select Month:", months)
        month = months.index(month_name) + 1  # Convert month name to month number
        
        # Get the current year
        year = datetime.now().year
        cal = calendar.monthcalendar(year, month)
        
        # Create a dictionary to map due dates to task details
        task_dict = {}
        for task in user_tasks:
            task_dict[task.due_date] = {
                'task_name': task.task_name,
                'time_estimate': task.time_estimate,
                'time_due': task.time_due,
                'done': task.done
            }
        
        # Render the calendar string
        calendar_str = f"### Calendar for {month_name} {year}\n\n"
        calendar_str += "<table style='width:100%; text-align:center;'>"
        calendar_str += "<tr><th>Mon</th><th>Tue</th><th>Wed</th><th>Thu</th><th>Fri</th><th>Sat</th><th>Sun</th></tr>"
        
        for week in cal:
            row = "<tr>"
            for day in week:
                if day == 0:
                    row += "<td></td>"  # Empty cell for days not in the month
                else:
                    task_for_day = task_dict.get(datetime(year, month, day).date(), None)
                    task_label = f" ({task_for_day['task_name']})" if task_for_day else ""
                    task_color = "background-color: lightgreen;" if task_for_day and task_for_day['done'] else "background-color: lightcoral;"
                    row += f'<td style="{task_color}">{day}{task_label}</td>'
            row += "</tr>"
            calendar_str += row
        
        calendar_str += "</table>"
        st.markdown(calendar_str, unsafe_allow_html=True)

        # Task List Display below the calendar
        st.write("### Task List")

        # Prepare task details for display below the calendar
        task_details = {
            'Task': task_names,
            'Due Date': task_dates,
            "Time due": task_time_due,
            'Estimated Time': task_time_estimate,
            'Status': ['Done' if task.done else 'Pending' for task in user_tasks]
        }

        # Create a DataFrame with the task details and reset the index
        df_tasks = pd.DataFrame(task_details)
        df_tasks.index = range(1, len(df_tasks) + 1)  # Ensure the index starts from 1

        # Color the status column
        df_tasks['Status'] = df_tasks['Status'].apply(lambda x: f'<span style="color: {"green" if x == "Done" else "red"}">{x}</span>')

        # Display the task details in a DataFrame with styled HTML
        st.write(df_tasks.to_html(escape=False), unsafe_allow_html=True)


def search_tasks():
    if st.session_state.current_user:
        st.subheader("Search Tasks")
        search_term = st.text_input("Search by task name:")
        if search_term:
            filtered_tasks = Task.select().where(
                (Task.user == st.session_state.current_user) & 
                (Task.task_name.contains(search_term))
            )
            if filtered_tasks:
                st.write("Filtered Tasks:")
                for i, task in enumerate(filtered_tasks, 1):
                    st.write(f"{i}. Task: {task.task_name}, Due Date: {task.due_date}, Time Due: {task.time_due}")
            else:
                st.warning("No tasks found with that name.")


def delete_task():
    if st.session_state.current_user:
        st.subheader("Delete Task")
        user_tasks = Task.select().where(Task.user == st.session_state.current_user)
        task_options = [(task.task_name, task.id) for task in user_tasks]
        selected_task = st.selectbox("Select task to delete:", task_options, format_func=lambda x: x[0])
        if st.button("Delete Task", key="delete_task_button"):
            Task.get(Task.id == selected_task[1]).delete_instance()
            st.success(f"Task '{selected_task[0]}' deleted successfully.")


def update_task():
    if st.session_state.current_user:
        st.subheader("Update Task")
        user_tasks = Task.select().where(Task.user == st.session_state.current_user)
        task_options = [(task.task_name, task.id) for task in user_tasks]
        selected_task = st.selectbox("Select task to update:", task_options, format_func=lambda x: x[0])
        
        if selected_task:
            task = Task.get(Task.id == selected_task[1])
            new_name = st.text_input("Task name:", value=task.task_name)
            new_due_date = st.date_input("Due date:", value=task.due_date)
            new_time_due = st.time_input("Time due:" ,value = task.time_due)
            if st.button("Update Task", key="update_task_button"):
                task.task_name = new_name
                task.due_date = new_due_date
                task.time_due = new_time_due
                task.save()
                st.success("Task updated successfully.")


def mark_task_done():
    if st.session_state.current_user:
        st.subheader("Mark Task As Done")
        user_tasks = Task.select().where(Task.user == st.session_state.current_user)
        task_options = [(task.task_name, task.id) for task in user_tasks]
        selected_task = st.selectbox("Select task to mark as done:", task_options, format_func=lambda x: x[0])

        if st.button("Mark Task As Done", key="mark_task_button"):
            task = Task.get(Task.id == selected_task[1])
            task.done = True
            task.save()
            st.success(f"Task '{task.task_name}' marked as done.")


def generate_smart_schedule():
    if st.session_state.current_user is None:
        st.warning("Please log in to generate a smart schedule.")
        return

    user_tasks = Task.select().where(Task.user == st.session_state.current_user)

    do_first = []
    schedule = []
    delegate = []
    eliminate = []

    for task in user_tasks:
        if task.urgency and task.importance:
            do_first.append(task)
        elif not task.urgency and task.importance:
            schedule.append(task)
        elif task.urgency and not task.importance:
            delegate.append(task)
        else:
            eliminate.append(task)

    st.subheader("Do First (Urgent & Important):")
    for i, task in enumerate(do_first, 1):
        st.write(f"{i}. Task: {task.task_name}, Deadline: {task.due_date}, Estimated Time: {task.time_estimate} mins")

    st.subheader("Schedule for Later (Important, Not Urgent):")
    for i, task in enumerate(schedule, 1):
        st.write(f"{i}. Task: {task.task_name}, Deadline: {task.due_date}, Estimated Time: {task.time_estimate} mins")

    st.subheader("Delegate (Urgent, Not Important):")
    for i, task in enumerate(delegate, 1):
        st.write(f"{i}. Task: {task.task_name}, Deadline: {task.due_date}, Estimated Time: {task.time_estimate} mins")

    st.subheader("Eliminate (Not Urgent & Not Important):")
    for i, task in enumerate(eliminate, 1):
        st.write(f"{i}. Task: {task.task_name}, Deadline: {task.due_date}, Estimated Time: {task.time_estimate} mins")


def display_menu():
    st.sidebar.header("Menu")
    if st.sidebar.button("Add Task", key="another_add_task_button"):
        switch_page("Add Task")
    if st.sidebar.button("View Tasks"):
        switch_page("View Tasks")
    if st.sidebar.button("Search Tasks"):
        switch_page("Search Tasks")
    if st.sidebar.button("Delete Task", key="another_delete_task_button"):
        switch_page("Delete Task")
    if st.sidebar.button("Update Task", key="another_update_task_button"):
        switch_page("Update Task")
    if st.sidebar.button("Mark Task As Done", key="another_mark_task_button"):
        switch_page("Mark Task As Done")
    if st.sidebar.button("Generate Smart Schedule"):
        switch_page("Generate Smart Schedule")
    st.sidebar.button("Logout", on_click=logout_user)


def main():
    st.title("TooDles")
    
    if st.session_state.current_user is None:
        choice = st.radio("Login to existing account or register to create a new one", ("Login", "Register"))
        if choice == "Login":
            login_user()
        elif choice == "Register":
            register_user()
    else:
        display_menu()
        
        check_notifications_and_alarm()

        if st.session_state.page == 'Add Task':
            add_task()
        elif st.session_state.page == 'Search Tasks':
            search_tasks()
        elif st.session_state.page == 'Update Task':
            update_task()
        elif st.session_state.page == 'View Tasks':
            view_tasks()
        elif st.session_state.page == 'Delete Task':
            delete_task()
        elif st.session_state.page == 'Mark Task As Done':
            mark_task_done()
        elif st.session_state.page == 'Generate Smart Schedule':
            generate_smart_schedule()

main()