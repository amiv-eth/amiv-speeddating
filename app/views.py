from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from flask import Flask, render_template, request, redirect, url_for, flash
from app.models import Events, TimeSlots, Participants
from app.forms import MultiCheckboxField, LoginForm, CreateEventForm, CreateTimeSlotForm, SignupForm, ChangeDateNr
from app.help_queries import get_string_of_date_list, get_list_women_of_slot, get_list_men_of_slot, get_string_mails_of_list
from app.functions import get_age, export, change_datenr, change_payed, change_present, event_change_register_status, event_change_active_status, event_change_signup_status
from app import app, db, login_manager
from datetime import datetime
from app.users import User, check_credentials

# class User(UserMixin):
#     pass


@login_manager.user_loader
def user_loader(username):
    if username not in app.config['USERS'].keys():
        return
    user = User()
    user.id = username
    return user


# index page
@app.route('/')
@app.route('/index')
def index():
    try:
        event = Events.query.filter(Events.Active == '1').first()
        dates = None
        if event != None:
            timeslots = TimeSlots.query.filter(
                TimeSlots.EventID == event.ID).all()
            dates = list(set(list(slot.Date for slot in timeslots)))
        dates_string = get_string_of_date_list(dates)
    except Exception as e:
        print(e)
        return render_template('error.html')
    return render_template('index.html', event=event, dates=dates_string)


# login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        fusername = request.form['username']
        fpassword = request.form['password']
        if check_credentials(fusername, fpassword) == True:
            user = User()
            user.id = fusername
            login_user(user)
            return redirect(url_for('admin'))
        else:
            render_template('login.html', form=form)
    return render_template('login.html', form=form)


# logout page
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('admin'))


# unauthorized handler redirecting to index
@login_manager.unauthorized_handler
def unauthorized_handler():
    return redirect('/')


# protected admin overview page
@app.route('/admin', methods=["GET", "POST"])
@login_required
def admin():
    events = None
    if request.method == 'GET':
        try:
            events = Events.query.all()
        except Exception as e:
            print(e)
            return render_template('error.html')
    return render_template('admin.html', events=events)


# protected admin event view page
@app.route('/event_view/<int:event_id>', methods=["GET", "POST"])
@login_required
def event_view(event_id):
    if request.method == 'GET':
        slots = None
        eventname = None
        try:
            slots = TimeSlots.query.filter(TimeSlots.EventID == event_id)
            event = Events.query.filter(Events.ID == event_id).first()
        except Exception as e:
            print(e)
            return render_template('error.html')
        return render_template('event_view.html', slots=slots, event=event)


# protected admin event view page
@app.route('/event_participants/<int:event_id>', methods=["GET", "POST"])
@login_required
def event_participants(event_id):
    if request.method == 'GET':
        eid = event_id
        slots = None
        eventname = None
        women = []
        men = []
        inw = []
        inm = []
        mailinw = []
        mailoutw = []
        mailinm = []
        mailoutm = []

        try:
            event = Events.query.filter(Events.ID == eid).first()
            slots = TimeSlots.query.filter(TimeSlots.EventID == eid)
            if slots != None:
                for slot in slots:
                    w = Participants.query.order_by(
                        (Participants.CreationTimestamp)).filter(
                            Participants.EventID == eid,
                            Participants.AvailableSlot == slot.ID,
                            Participants.Gender == '1').all()
                    m = Participants.query.order_by(
                        (Participants.CreationTimestamp)).filter(
                            Participants.EventID == eid,
                            Participants.AvailableSlot == slot.ID,
                            Participants.Gender == '0').all()
                    women.append(w)
                    men.append(m)
        except Exception as e:
            print(e)
            return render_template('error.html')

    for wslot in women:
        inmail = ""
        outmail = ""
        wcount = 0
        for w in wslot:
            if w.Confirmed == 1 and wcount < 12:
                wcount = wcount + 1
                inw.append(w.EMail)
                inmail = inmail + w.EMail + "; "
            else:
                outmail = outmail + w.EMail + "; "

        mailinw.append(inmail)
        mailoutw.append(outmail)

    for mslot in men:
        inmail = ""
        outmail = ""
        mcount = 0
        for m in mslot:
            if m.Confirmed == 1 and mcount < 12:
                mcount = mcount + 1
                inm.append(m.EMail)
                inmail = inmail + m.EMail + "; "
            else:
                outmail = outmail + m.EMail + "; "
        mailinm.append(inmail)
        mailoutm.append(outmail)

    return render_template(
        'event_participants.html',
        event=event,
        slots=slots,
        women=women,
        men=men,
        inw=inw,
        inm=inm,
        mailinw=mailinw,
        mailinm=mailinm,
        mailoutw=mailoutw,
        mailoutm=mailoutm)


# protected admin create new event page
@app.route('/create_event', methods=["GET", "POST"])
@login_required
def create_event():
    form = CreateEventForm(request.form)
    if request.method == 'POST' and form.validate():
        try:
            format = '%Y-%m-%dT%H:%M'
            name = str(request.form['name'])
            year = int(request.form['year'])
            semester = int(request.form['semester'])
            specialslot = int(request.form['specialslot'])
            specialslotname = str(request.form['specialslotname'])
            specialslotdescription = str(
                request.form['specialslotdescription'])
            timestamp = datetime.now()
            opensignuptimestamp = datetime.strptime(
                str(request.form['opensignuptimestamp']), format)
            closesignuptimestamp = datetime.strptime(
                str(request.form['closesignuptimestamp']), format)
            place = str(request.form['place'])
            participationfee = str(request.form['participationfee'])
            signup_open = 0
            active = 0

        except Exception as e:
            print(e)
            return render_template(
                'error.html', message=str(request.form['opensignuptimestamp']))

        try:
            event = Events(name, year, specialslot, specialslotname,
                           specialslotdescription, place, semester, timestamp,
                           signup_open, active, participationfee,
                           opensignuptimestamp, closesignuptimestamp)
            db.session.add(event)
            db.session.commit()
        except Exception as e:
            print(e)
            return render_template('error.html')
        return redirect(url_for('admin'))
    return render_template('create_event.html', form=form)


# protected admin create new timeslot of an event page
@app.route('/create_timeslot/<int:event_id>', methods=["GET", "POST"])
@login_required
def create_timeslot(event_id):
    form = CreateTimeSlotForm(request.form)
    eventid = event_id
    if request.method == 'POST' and form.validate():
        try:
            date = str(request.form['date'])
            starttime = str(request.form['starttime'])
            endtime = str(request.form['endtime'])
            nrcouples = int(request.form['nrcouples'])
            agerange = int(request.form['agerange'])
            specialslot = int(request.form['specialslot'])
            slot = TimeSlots(eventid, date, starttime, endtime, nrcouples,
                             agerange, specialslot)
            db.session.add(slot)
            db.session.commit()

        except Exception as e:
            print(e)
            return render_template('error.html')

        return redirect(url_for('event_view', event_id=eventid))
    return render_template('create_timeslot.html', eid=eventid, form=form)


@app.route('/timeslot_view/<int:timeslot_id>', methods=["GET", "POST"])
@login_required
def timeslot_view(timeslot_id):
    if request.method == 'GET':
        
        slotid = timeslot_id
        participants = None
        inw = []
        inm = []

        [w_in, w_out] = get_list_women_of_slot(db.session, timeslot_id)
        [m_in, m_out] = get_list_men_of_slot(db.session, timeslot_id)

        try:
            slot = TimeSlots.query.filter(TimeSlots.ID == slotid).first()
            women = Participants.query.order_by(
                (Participants.CreationTimestamp)).filter(
                    Participants.AvailableSlot == slotid,
                    Participants.Gender == '1').all()
            men = Participants.query.order_by(
                (Participants.CreationTimestamp)).filter(
                    Participants.AvailableSlot == slotid,
                    Participants.Gender == '0').all()
            event = Events.query.filter(Events.ID == slot.EventID).first()
        except Exception as e:
            print(e)
            return render_template('error.html')

        w_in_mail = get_string_mails_of_list(db.session, slot, w_in)
        w_out_mail = get_string_mails_of_list(db.session, slot, w_out)
        m_in_mail = get_string_mails_of_list(db.session, slot, m_in)
        m_out_mail = get_string_mails_of_list(db.session, slot, m_out)

        return render_template(
            'timeslot_view.html',
            event=event,
            slot=slot,
            women=women,
            men=men,
            inw=w_in,
            inm=m_in,
            mailinw=w_in_mail,
            mailinm=m_in_mail,
            mailoutw=w_out_mail,
            mailoutm=m_out_mail)


@app.route('/timeslot_view_ongoing/<int:timeslot_id>', methods=["GET", "POST"])
@login_required
def timeslot_view_ongoing(timeslot_id):
    form = ChangeDateNr(request.form)
    csv = ''

    if request.method == 'POST' and form.validate():
        try:
            participant_id = int(request.form['participant_id'])
            datenr = int(request.form['datenr'])
            changed = change_datenr(db.session, participant_id, datenr)

        except Exception as e:
            print(e)
            return render_template('error.html')

    # "GET":
    try:
        slot = TimeSlots.query.filter(TimeSlots.ID == timeslot_id).first()
        women = Participants.query.order_by(
            (Participants.CreationTimestamp)).filter(
                Participants.AvailableSlot == timeslot_id,
                Participants.Gender == '1', Participants.Present == '1').all()
        men = Participants.query.order_by(
            (Participants.CreationTimestamp)).filter(
                Participants.AvailableSlot == timeslot_id,
                Participants.Gender == '0', Participants.Present == '1').all()
        event = Events.query.filter(Events.ID == slot.EventID).first()
    except Exception as e:
        print(e)
        return render_template('error.html')
    form.datenr.data = ''
    return render_template(
        'timeslot_view_ongoing.html',
        event=event,
        slot=slot,
        women=women,
        men=men,
        form=form,
        csv=csv)


# link for open/cose the signup
@app.route('/change_signup/<int:event_id>/<int:open>', methods=["GET", "POST"])
@login_required
def change_signup(event_id, open):
    try:
        changed = event_change_signup_status(db.session, event_id, open)
    except Exception as e:
        print(e)
        return render_template('error.html')
    if changed:
        return redirect(url_for('admin'))
    return render_template('error.html')


# link for activate an event ## TODO merge to one single function
@app.route(
    '/activate_event/<int:event_id>/<int:active>', methods=["GET", "POST"])
@login_required
def activate_event(event_id, active):
    try:
        activated = event_change_active_status(db.session, event_id, active)
    except Exception as e:
        print(e)
        return render_template('error.html')
    if activated:
        return redirect(url_for('admin'))
    return render_template('error.html')


# link for register/deregister an participant ## TODO merge to one single function
@app.route(
    '/register_participant/<int:event_id>/<int:participant_id>/<int:register>',
    methods=["GET", "POST"])
@login_required
def register_participant(event_id, participant_id, register):
    try:
        registered = event_change_register_status(db.session, participant_id,
                                                  register)
    except Exception as e:
        print(e)
        return render_template('error.html')
    if registered:
        return redirect(url_for('event_participants', event_id=event_id))
    return render_template('error.html')


@app.route(
    '/change_participant_on_timeslot/<int:slot_id>/<int:participant_id>/<string:action>',
    methods=["GET", "POST"])
@login_required
def change_participant_on_timeslot(slot_id, participant_id, action):
    try:
        if action == 'present':
            changed = change_present(db.session, slot_id, participant_id)
        elif action == 'payed':
            changed = change_payed(db.session, slot_id, participant_id)
    except Exception as e:
        print(e)
        return render_template('error.html')
    if changed:
        return redirect(url_for('timeslot_view', timeslot_id=slot_id))
    return render_template(
        'error.html',
        message='changing ' + action +
        ' did not work. Maybe a participant wanted to pay before being present on event.'
    )


# signup page
@app.route('/signup', methods=["GET", "POST"])
def signup():
    form = SignupForm(request.form)
    try:
        event = Events.query.filter(Events.Active == '1').first()
        if event != None:
            eventid = event.ID
            timeslots = TimeSlots.query.filter(
                TimeSlots.EventID == eventid).all()
            if timeslots != None:
                age_strings = []
                age_strings.append('< 22'.ljust(6))
                age_strings.append('22-25'.ljust(6))
                age_strings.append('> 25'.ljust(6))
                age_strings.append('alle'.ljust(6))
                ids_nonspecial = []
                ids_special = []
                strings_non_special = []
                strings_special = []
                for s in timeslots:
                    if s.SpecialSlot == 1:
                        ids_special.append(int(s.ID))
                        women = Participants.query.filter(
                            Participants.AvailableSlot == s.ID,
                            Participants.Confirmed == '1',
                            Participants.Gender == '1').count()
                        men = Participants.query.filter(
                            Participants.AvailableSlot == s.ID,
                            Participants.Confirmed == '1',
                            Participants.Gender == '0').count()
                        stri = '&nbsp &nbsp &nbsp'
                        stri = stri + \
                            s.Date.strftime("%a %d. %b %y") + \
                            '&nbsp &nbsp &nbsp'
                        stri = str(stri).ljust(50, ' ' [0:1]) + str(
                            s.StartTime)[:-3] + ' - ' + str(s.EndTime)[:-3]
                        stri = stri + '&nbsp &nbsp &nbsp'
                        stri = stri + 'Altersgruppe: &nbsp' + \
                            age_strings[s.AgeRange]
                        stri = stri + '&nbsp &nbsp &nbsp Anmeldungsstand: &nbsp &nbsp  M: ' + \
                            str(men) + '/' + str(s.NrCouples)
                        stri = stri + '&nbsp &nbsp W: ' + \
                            str(women) + '/' + str(s.NrCouples)
                        strings_special.append(stri)
                    elif s.SpecialSlot == 0:
                        ids_nonspecial.append(int(s.ID))
                        women = Participants.query.filter(
                            Participants.AvailableSlot == s.ID,
                            Participants.Confirmed == '1',
                            Participants.Gender == '1').count()
                        men = Participants.query.filter(
                            Participants.AvailableSlot == s.ID,
                            Participants.Confirmed == '1',
                            Participants.Gender == '0').count()
                        stri = '&nbsp &nbsp &nbsp'
                        stri = stri + \
                            s.Date.strftime("%a %d. %b %y") + \
                            '&nbsp &nbsp &nbsp'
                        stri = str(stri).ljust(50, ' ' [0:1]) + str(
                            s.StartTime)[:-3] + ' - ' + str(s.EndTime)[:-3]
                        stri = stri + '&nbsp &nbsp &nbsp'
                        stri = stri + 'Altersgruppe: &nbsp' + \
                            age_strings[s.AgeRange]
                        stri = stri + '&nbsp &nbsp &nbsp Anmeldungsstand: &nbsp &nbsp  M: ' + \
                            str(men) + '/' + str(s.NrCouples)
                        stri = stri + '&nbsp &nbsp W: ' + \
                            str(women) + '/' + str(s.NrCouples)
                        strings_non_special.append(stri)

                form.availableslots.choices = [
                    (ids_nonspecial[i], strings_non_special[i])
                    for i in range(0, len(ids_nonspecial))
                ]
                form.availablespecialslots.choices = [
                    (ids_special[i], strings_special[i])
                    for i in range(0, len(ids_special))
                ]

    except Exception as e:
        print(e)
        return render_template('error.html')

    if request.method == 'POST' and form.validate():
        try:
            timestamp = datetime.now()
            name = str(request.form['name'])
            prename = str(request.form['prename'])
            gender = int(request.form['gender'])
            email = str(request.form['email'])
            mobile = str(request.form['mobilenr'])
            address = str(request.form['address'])
            birthday = str(request.form['birthday'])
            studycourse = str(request.form['studycourse'])
            studysemester = str(request.form['studysemester'])
            perfectdate = str(request.form['perfectdate'])
            fruit = str(request.form['fruit'])
            if event.SpecialSlots == 1:
                availablespecialslots = request.form.getlist(
                    'availablespecialslots')
            availableslots = request.form.getlist('availableslots')
            confirmed = 1
            present = 0
            payed = 0

            slots = 0
            if availableslots:
                slots = int(availableslots[0])
            elif availablespecialslots:
                slots = int(availablespecialslots[0])
            else:
                message = 'Du hast kein passendes Datum ausgewählt! Bitte geh zurück und wähle ein dir passendes Datum aus.'
                return render_template('error.html', message=message)

            bday = datetime.strptime(birthday, '%d.%m.%Y')
            count = Participants.query.filter(
                Participants.EMail == email,
                Participants.EventID == eventid).count()
            chosen_timeslot = TimeSlots.query.filter(
                TimeSlots.ID == int(slots)).first()
            chosen_datetime = str(
                chosen_timeslot.Date.strftime("%a %d. %b %y")) + '  ' + str(
                    chosen_timeslot.StartTime)

            if count == 0:
                new_participant = Participants(
                    timestamp,
                    eventid,
                    name,
                    prename,
                    email,
                    mobile,
                    address,
                    bday,
                    gender,
                    course=studycourse,
                    semester=studysemester,
                    perfDate=perfectdate,
                    fruit=fruit,
                    aSlot=slots,
                    confirmed=confirmed,
                    present=present,
                    payed=payed)
                db.session.add(new_participant)
                db.session.commit()
            else:
                message = 'Die E-Mail Adresse ' + email + \
                    ' wurde bereits für das Speeddating angewendet. Bitte versuchen Sie es erneut mit einer neuen E-Mail Adresse.'
                return render_template('error.html', message=message)

        except Exception as e:
            print(e)
            return render_template('error.html')

        return render_template(
            'success.html',
            name=(prename + ' ' + name),
            mail=email,
            datetime=chosen_datetime)
    # else:
    #     if session:
    #         session.close()

    return render_template('signup.html', form=form, event=event)


# manual signup page
@app.route('/manual_signup', methods=["GET", "POST"])
def manual_signup():
    form = SignupForm(request.form)
    try:
        event = Events.query.filter(Events.Active == '1').first()
        if event != None:
            eventid = event.ID
            timeslots = TimeSlots.query.filter(
                TimeSlots.EventID == eventid).all()
            if timeslots != None:
                age_strings = []
                age_strings.append('< 22'.ljust(6))
                age_strings.append('22-25'.ljust(6))
                age_strings.append('> 25'.ljust(6))

                ids = []
                strings = []
                for s in timeslots:
                    ids.append(int(s.ID))
                    women = Participants.query.filter(
                        Participants.AvailableSlot == s.ID,
                        Participants.Confirmed == '1',
                        Participants.Gender == '1').count()
                    men = Participants.query.filter(
                        Participants.AvailableSlot == s.ID,
                        Participants.Confirmed == '1',
                        Participants.Gender == '0').count()
                    stri = '&nbsp &nbsp '
                    stri = stri + \
                        s.Date.strftime("%a %d. %B %Y") + '&nbsp &nbsp '
                    stri = str(stri).ljust(50, ' ' [0:1]) + str(
                        s.StartTime)[:-3] + ' - ' + str(s.EndTime)[:-3]
                    stri = stri + '&nbsp &nbsp '
                    stri = stri + 'Altersgruppe: &nbsp' + \
                        age_strings[s.AgeRange]
                    stri = stri + \
                        '&nbsp &nbsp # angemeldete Personen: &nbsp &nbsp  M: ' + \
                        str(men)
                    stri = stri + '&nbsp &nbsp W: ' + str(women)
                    strings.append(stri)

                form.availableslots.choices = [
                    (ids[i], strings[i]) for i in range(0, len(timeslots))
                ]

    except Exception as e:
        print(e)
        return render_template('error.html')

    if request.method == 'POST' and form.validate():
        try:
            timestamp = datetime.now()
            name = str(request.form['name'])
            prename = str(request.form['prename'])
            gender = int(request.form['gender'])
            email = str(request.form['email'])
            mobile = str(request.form['mobilenr'])
            address = str(request.form['address'])
            birthday = str(request.form['birthday'])
            studycourse = str(request.form['studycourse'])
            studysemester = str(request.form['studysemester'])
            perfectdate = str(request.form['perfectdate'])
            fruit = str(request.form['fruit'])
            availableslots = int(request.form['availableslots'])
            confirmed = 1
            present = 1
            payed = 0

            bday = datetime.strptime(birthday, '%d.%m.%Y')

            count = Participants.query.filter(
                Participants.EMail == email,
                Participants.EventID == eventid).count()

            if count == 0:
                new_participant = Participants(
                    timestamp,
                    eventid,
                    name,
                    prename,
                    email,
                    mobile,
                    address,
                    bday,
                    gender,
                    course=studycourse,
                    semester=studysemester,
                    perfDate=perfectdate,
                    fruit=fruit,
                    aSlot=availableslots,
                    confirmed=confirmed,
                    present=present,
                    payed=payed)
                db.session.add(new_participant)
                db.session.commit()
            else:
                message = 'Die E-Mail Adresse ' + email + \
                    ' wurde bereits für das Speeddating angewendet. Bitte versuchen Sie es erneut mit einer neuen E-Mail Adresse.'
                return render_template('error.html', message=message)

        except Exception as e:
            print(e)
            return render_template('error.html')

        return render_template('success.html')
    # else:
    #     if session:
    #         session.close()

    return render_template('manual_signup.html', form=form, event=event)


# link for exporting the participants of a slot for the SpeedMatchTool
@app.route('/export_slot/<int:timeslot_id>', methods=["GET", "POST"])
@login_required
def export_slot(timeslot_id):

    try:
        slot = TimeSlots.query.filter(TimeSlots.ID == timeslot_id).first()
        women = Participants.query.order_by(
            (Participants.CreationTimestamp)).filter(
                Participants.AvailableSlot == timeslot_id,
                Participants.Gender == '1', Participants.Present == '1').all()
        men = Participants.query.order_by(
            (Participants.CreationTimestamp)).filter(
                Participants.AvailableSlot == timeslot_id,
                Participants.Gender == '0', Participants.Present == '1').all()
        exported = export(women, men, slot)

    except Exception as e:
        print(e)
        return render_template('error.html')

    if exported != '':
        return render_template('csv.html', slot=slot, exported=exported)
    return render_template('error.html')