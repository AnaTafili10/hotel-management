import base64
import logging

from odoo import api, fields, models
from odoo import tools, _
from odoo.exceptions import ValidationError, AccessError
from odoo.modules.module import get_module_resource




class Client(models.Model):
    _name = "hotel.client"
    _description = "client"

    Identity_no = fields.Char(string="Identity Number", required=True)
    name = fields.Char(string="Name", required=True)
    surname = fields.Char(string="Surname", required=True)
    age = fields.Integer(string="Age", required=True)
    adr = fields.Char(string="Adr", required=True)
    phone = fields.Char(string="Phone", required=True)
    email = fields.Char(string="Email", required=True)
    active = fields.Boolean('Active', default=True, store=True)
    color = fields.Integer('Color Index', default=0)
    notes = fields.Text('Notes')
    # image: all image fields are base64 encoded and PIL-supported
    image = fields.Binary(
        "Photo", default='_default_image', attachment=True,
        help="This field holds the image used as photo for the employee, limited to 1024x1024px.")
    image_medium = fields.Binary(
        "Medium-sized photo", attachment=True,
        help="Medium-sized photo of the employee. It is automatically "
             "resized as a 128x128px image, with aspect ratio preserved. "
             "Use this field in form views or some kanban views.")
    image_small = fields.Binary(
        "Small-sized photo", attachment=True,
        help="Small-sized photo of the employee. It is automatically "
             "resized as a 64x64px image, with aspect ratio preserved. "
             "Use this field anywhere a small image is required.")

    @api.model
    def _default_image(self):
        image_path = get_module_resource('hotel', 'static/src/img', 'default_image.png')
        return tools.image_resize_image_big(base64.b64encode(open(image_path, 'rb').read()))

   #Unicity controll
    # _sql_constraints = ['Identity_no_uniq', 'unique(Identity_no)', "Identity number must be unique for every client"]

class Floor(models.Model):
        _name = "hotel.floor"
        _description = "floor"

        # name = fields.Char(string="Floor Name", required=True)
        number = fields.Integer(string="Floor")

class HotelRoom(models.Model):
    _name = 'hotel.room'
    _description = 'Hotel Room'

    name = fields.Char(string="Name", required=True)
    floor_id = fields.Many2one('hotel.floor', 'Floor No',
                               help='At which floor the room is located.')
    list_price = fields.Integer(string="Room rate")
    max_adult = fields.Integer('Max Adult')
    max_child = fields.Integer('Max Child')
    category_id = fields.Many2one('hotel.room.type', string='Room Category', required=True)
    status = fields.Selection([('available', 'Available'),
                               ('occupied', 'Occupied')],
                              'Status', default='available')
    capacity = fields.Integer('Capacity', required=True)
    # room_line_ids = fields.One2many('folio.room.line', 'room_ids',
    #                                 string='Room Reservation Line')
    room_reservation_line_ids = fields.One2many('hotel.room.reservation.line',
                                                'room_ids',
                                                string='Room Reserve Line')
    category_id = fields.Selection ([('single', 'Single'), ('double', 'Double'), ('triple', 'Triple'), ('deluxe', 'Deluxe'), ('suite', 'Suite')], string="Room Type")
    @api.constrains('capacity')
    def check_capacity(self):
        for room in self:
            if room.capacity <= 0:
                raise ValidationError(_('Room capacity must be more than 0'))

    @api.onchange('isroom')
    def isroom_change(self):
        '''
        Based on isroom, status will be updated.
        ----------------------------------------
        @param self: object pointer
        '''
        if self.isroom is False:
            self.status = 'occupied'
        if self.isroom is True:
            self.status = 'available'

    @api.multi
    def write(self, vals):
        """
        Overrides orm write method.
        @param self: The object pointer
        @param vals: dictionary of fields value.
        """
        if 'isroom' in vals and vals['isroom'] is False:
            vals.update({'color': 2, 'status': 'occupied'})
        if 'isroom' in vals and vals['isroom'] is True:
            vals.update({'color': 5, 'status': 'available'})
        ret_val = super(HotelRoom, self).write(vals)
        return ret_val

    @api.multi
    def set_room_status_occupied(self):
        """
        This method is used to change the state
        to occupied of the hotel room.
        ---------------------------------------
        @param self: object pointer
        """
        return self.write({'isroom': False, 'color': 2})

    @api.multi
    def set_room_status_available(self):
        """
        This method is used to change the state
        to available of the hotel room.
        ---------------------------------------
        @param self: object pointer
        """
        return self.write({'isroom': True, 'color': 5})

class RoomType(models.Model):
        _name = "hotel.room.type"
        _description = "Room Type"

        name = fields.Char(string="Name", required=True)
        category_id = fields.Many2one('hotel.room.type', 'Category')
        child_id = fields.One2many('hotel.room.type', 'category_id',
                                   'Child Categories')
        category_id = fields.Selection(
            [('single', 'Single'), ('double', 'Double'), ('triple', 'Triple'), ('deluxe', 'Deluxe'),
             ('suite', 'Suite')], string="Room Type")

        @api.multi
        def name_get(self):
            def get_names(cat):
                """ Return the list [cat.name, cat.category_id.name, ...] """
                res = []
                while cat:
                    res.append(cat.name)
                    cat = cat.categ_id
                return res

            return [(cat.id, " / ".join(reversed(get_names(cat)))) for cat in self]

        @api.model
        def name_search(self, name, args=None, operator='ilike', limit=100):
            if not args:
                args = []
            if name:
                # Be sure name_search is symetric to name_get
                category_names = name.split(' / ')
                parents = list(category_names)
                child = parents.pop()
                domain = [('name', operator, child)]
                if parents:
                    names_ids = self.name_search(' / '.join(parents), args=args,
                                                 operator='ilike', limit=limit)
                    category_ids = [name_id[0] for name_id in names_ids]
                    if operator in expression.NEGATIVE_TERM_OPERATORS:
                        categories = self.search([('id', 'not in', category_ids)])
                        domain = expression.OR([[('category_id', 'in',
                                                  categories.ids)], domain])
                    else:
                        domain = expression.AND([[('category_id', 'in',
                                                   category_ids)], domain])
                    for i in range(1, len(category_names)):
                        domain = [[('name', operator,
                                    ' / '.join(category_names[-1 - i:]))], domain]
                        if operator in expression.NEGATIVE_TERM_OPERATORS:
                            domain = expression.AND(domain)
                        else:
                            domain = expression.OR(domain)
                categories = self.search(expression.AND([domain, args]),
                                         limit=limit)
            else:
                categories = self.search(args, limit=limit)
            return categories.name_get()


class HotelReservation(models.Model):

    _name = "hotel.reservation"
    _rec_name = "reservation_no"
    _description = "Reservation"

    reservation_no = fields.Char('Reservation No', size=64, readonly=True)

    checkin = fields.Datetime('Expected-Date-Arrival', required=True,
                              readonly=True,
                              states={'draft': [('readonly', False)]})
    checkout = fields.Datetime('Expected-Date-Departure', required=True,
                               readonly=True,
                               states={'draft': [('readonly', False)]})
    adults = fields.Integer('Adults', size=64, readonly=True,
                            states={'draft': [('readonly', False)]},
                            help='List of adults there in guest list. ')
    children = fields.Integer('Children', size=64, readonly=True,
                              states={'draft': [('readonly', False)]},
                              help='Number of children there in guest list.')
    reservation_line = fields.One2many('hotel_reservation.line', 'line_id',
                                       'Reservation Line',
                                       help='Hotel room reservation details.',
                                       readonly=True,
                                       states={'draft': [('readonly', False)]})
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'),
                              ('cancel', 'Cancel'), ('done', 'Done')],
                             'State', readonly=True,
                             default=lambda *a: 'draft')
    # folio_id = fields.Many2many('hotel.folio', 'hotel_folio_reservation_rel',
    #                              string='Folio')
    dummy = fields.Datetime('Dummy')
#
    @api.multi
    def unlink(self):
        """
        Overrides orm unlink method.
        @param self: The object pointer
        @return: True/False.
        """
        for reserv_rec in self:
            if reserv_rec.state != 'draft':
                raise ValidationError(_('You cannot delete Reservation in %s\
                   state.') % (reserv_rec.state))
        return super(HotelReservation, self).unlink()
# #
    @api.constrains('reservation_line', 'adults', 'children')
    def check_reservation_rooms(self):
        '''
        This method is used to validate the reservation_line.
        -----------------------------------------------------
        @param self: object pointer
        @return: raise a warning depending on the validation
        '''
        for reservation in self:
            cap = 0
            for rec in reservation.reservation_line:
                if len(rec.reserve) == 0:
                    raise ValidationError(_('Please Select Rooms \
                        For Reservation.'))
                for room in rec.reserve:
                    cap += room.capacity
            if (reservation.adults + reservation.children) > cap:
                raise ValidationError(_('Room Capacity Exceeded \n Please \
                                            Select Rooms According to Members \
                                            Accomodation.'))
            if reservation.adults <= 0:
                raise ValidationError(_('Adults must be more than 0'))

            @api.model
            def _needaction_count(self, domain=None):
                """
                 Show a count of draft state reservations on the menu badge.
                 """
                return self.search_count([('state', '=', 'draft')])

        @api.multi
        def confirmed_reservation(self):
            """
            This method create a new recordset for hotel room reservation line
            ------------------------------------------------------------------
            @param self: The object pointer
            @return: new record set for hotel room reservation line.
            """
            reservation_line_obj = self.env['hotel.room.reservation.line']
            for reservation in self:
                for line_id in reservation.reservation_line:
                    for room_ids in line_id.reserve:
                        if room_ids.room_reservation_line_ids:
                            for reserv in room_ids.room_reservation_line_ids. \
                                    search([('status', '=', 'confirm')]):
                                reserv_checkin = datetime. \
                                    strptime(reservation.checkin, dt)
                                reserv_checkout = datetime. \
                                    strptime(reservation.checkout, dt)
                                check_in = datetime.strptime(reserv.check_in, dt)
                                check_out = datetime.strptime(reserv.check_out, dt)
                                range1 = [reserv_checkin, reserv_checkout]
                                range2 = [check_in, check_out]
                                overlap_dates = self.check_overlap(*range1) \
                                                & self.check_overlap(*range2)
                                if overlap_dates:
                                    overlap_dates = [datetime.
                                                         strftime(dates,
                                                                  '%d/%m/%Y') for
                                                     dates in overlap_dates]
                                    raise ValidationError(_('You tried to Confirm '
                                                            'reservation with room'
                                                            ' those already '
                                                            'reserved in this '
                                                            'Reservation Period. '
                                                            'Overlap Dates are '
                                                            '%s') % overlap_dates)
                                else:
                                    self.state = 'confirm'
                                    for room_ids in line_id.reserve:
                                        vals = {'room_ids': room_ids.id,
                                                'check_in': reservation.checkin,
                                                'check_out': reservation.checkout,
                                                'state': 'assigned',
                                                'reservation_id': reservation.id,
                                                }
                                        room_ids.write({'isroom': False,
                                                       'status': 'occupied'})
                                        reservation_line_obj.create(vals)
                        else:
                            self.state = 'confirm'
                            for room_ids in line_id.reserve:
                                vals = {'room_ids': room_ids.id,
                                        'check_in': reservation.checkin,
                                        'check_out': reservation.checkout,
                                        'state': 'assigned',
                                        'reservation_id': reservation.id,
                                        }
                                room_ids.write({'isroom': False,
                                               'status': 'occupied'})
                                reservation_line_obj.create(vals)
                                return True
#
                    @api.multi
                    def cancel_reservation(self):
                        """
                        This method cancel recordset for hotel room reservation line
                        ------------------------------------------------------------------
                        @param self: The object pointer
                        @return: cancel record set for hotel room reservation line.
                        """
                        room_res_line_obj = self.env['hotel.room.reservation.line']
                        hotel_res_line_obj = self.env['hotel_reservation.line']
                        self.state = 'cancel'
                        room_reservation_line = room_res_line_obj.search([('reservation_id',
                                                                           'in', self.ids)])
                        room_reservation_line.write({'state': 'unassigned'})
                        reservation_lines = hotel_res_line_obj.search([('line_id',
                                                                        'in', self.ids)])
                        for reservation_line in reservation_lines:
                            reservation_line.reserve.write({'isroom': True,
                                                            'status': 'available'})
                        return True

                    @api.multi
                    def set_to_draft_reservation(self):
                        self.state = 'draft'
                        return True
# #
class HotelReservationLine(models.Model):

    _name = "hotel_reservation.line"
    _description = "Reservation Line"

    name = fields.Char('Name', size=64)
    line_id = fields.Many2one('hotel.reservation')
    reserve = fields.Many2many('hotel.room',
                               'hotel_reservation_line_room_rel',
                               'hotel_reservation_line_id', 'room_ids',
                               domain="[('isroom','=',True),\
                               ('category_id','=',category_id)]")
    category_id = fields.Many2one('hotel.room.type', 'Room Type')
# #
# #
@api.onchange('category_id')
def on_change_category(self):
    '''
    When you change categ_id it check checkin and checkout are
    filled or not if not then raise warning
    -----------------------------------------------------------
    @param self: object pointer
    '''
    hotel_room_obj = self.env['hotel.room']
    hotel_room_ids = hotel_room_obj.search([('category_id', '=',
                                             self.categ_id.id)])
    room_ids = []
    if not self.line_id.checkin:
        raise except_orm(_('Warning'),
                         _('Before choosing a room,\n You have to select \
                                a Check in date or a Check out date in \
                                the reservation form.'))
    for room in hotel_room_ids:
        assigned = False
        for line in room.room_reservation_line_ids:
            if line.status != 'cancel':
                if (self.line_id.checkin <= line.check_in <=
                    self.line_id.checkout) or (self.line_id.checkin <=
                                               line.check_out <=
                                               self.line_id.checkout):
                    assigned = True
                elif (line.check_in <= self.line_id.checkin <=
                      line.check_out) or (line.check_in <=
                                          self.line_id.checkout <=
                                          line.check_out):
                    assigned = True
        for rm_line in room.room_line_ids:
            if rm_line.status != 'cancel':
                if (self.line_id.checkin <= rm_line.check_in <=
                    self.line_id.checkout) or (self.line_id.checkin <=
                                               rm_line.check_out <=
                                               self.line_id.checkout):
                    assigned = True
                elif (rm_line.check_in <= self.line_id.checkin <=
                      rm_line.check_out) or (rm_line.check_in <=
                                             self.line_id.checkout <=
                                             rm_line.check_out):
                    assigned = True
        if not assigned:
            room_ids.append(room.id)
    domain = {'reserve': [('id', 'in', room_ids)]}
    return {'domain': domain}
#
    @api.multi
    def unlink(self):
        """
        Overrides orm unlink method.
        @param self: The object pointer
        @return: True/False.
        """
        hotel_room_reserv_line_obj = self.env['hotel.room.reservation.line']
        for reserv_rec in self:
            for rec in reserv_rec.reserve:
                hres_arg = [('room_id', '=', rec.id),
                            ('reservation_id', '=', reserv_rec.line_id.id)]
                myobj = hotel_room_reserv_line_obj.search(hres_arg)
                if myobj.ids:
                    rec.write({'isroom': True, 'status': 'available'})
                    myobj.unlink()
        return super(HotelReservationLine, self).unlink()
# #
class HotelRoomReservationLine(models.Model):
    _name = 'hotel.room.reservation.line'
    _description = 'Hotel Room Reservation'
    _rec_name = 'room_ids'

    room_ids = fields.Many2one('hotel.room', string='Room id')
    check_in = fields.Datetime('Check In Date', required=True)
    check_out = fields.Datetime('Check Out Date', required=True)
    state = fields.Selection([('assigned', 'Assigned'),
                              ('unassigned', 'Unassigned')], 'Room Status')
    reservation_id = fields.Many2one('hotel.reservation',
                                     string='Reservation')
    status = fields.Selection(string='state', related='reservation_id.state')
# #
    @api.multi
    def unlink(self):
        """
        Overrides orm unlink method.
        @param self: The object pointer
        @return: True/False.
        """
        for room in self:
            for reserv_line in room.room_reservation_line_ids:
                if reserv_line.status == 'confirm':
                    raise ValidationError(_('User is not able to delete the \
                                               room after the room in %s state \
                                               in reservation')
                                          % (reserv_line.status))
        return super(HotelRoom, self).unlink()
# #
    @api.model
    def cron_room_line(self):
        """
        This method is for scheduler
        every 1min scheduler will call this method and check Status of
        room is occupied or available
        --------------------------------------------------------------
        @param self: The object pointer
        @return: update status of hotel room reservation line
        """
        reservation_line_obj = self.env['hotel.room.reservation.line']
        folio_room_line_obj = self.env['folio.room.line']
        now = datetime.datetime.now()
        curr_date = now.strftime(dt)
        for room in self.search([]):
            reserv_line_ids = [reservation_line.ids for
                               reservation_line in
                               room.room_reservation_line_ids]
            reserv_args = [('id', 'in', reserv_line_ids),
                           ('check_in', '<=', curr_date),
                           ('check_out', '>=', curr_date)]
            reservation_line_ids = reservation_line_obj.search(reserv_args)
            rooms_ids = [room_line.ids for room_line in room.room_line_ids]
            rom_args = [('id', 'in', rooms_ids),
                        ('check_in', '<=', curr_date),
                        ('check_out', '>=', curr_date)]
            room_line_ids = folio_room_line_obj.search(rom_args)
            status = {'isroom': True, 'color': 5}
            if reservation_line_ids.ids:
                status = {'isroom': False, 'color': 2}
            room.write(status)
            if room_line_ids.ids:
                status = {'isroom': False, 'color': 2}
            room.write(status)
            if reservation_line_ids.ids and room_line_ids.ids:
                raise except_orm(_('Wrong Entry'),
                                 _('Please Check Rooms Status \
                                    for %s.' % (room.name)))
        return True
#
class RoomReservationSummary(models.Model):
    _name = 'room.reservation.summary'
    _description = 'Room reservation summary'

    name = fields.Char('Reservation Summary', default='Reservations Summary',
                       invisible=True)
    date_from = fields.Datetime('Date From')
    date_to = fields.Datetime('Date To')
    summary_header = fields.Text('Summary Header')
    room_summary = fields.Text('Room Summary')
# #
    @api.multi
    def room_reservation(self):
        '''
        @param self: object pointer
        '''
        mod_obj = self.env['ir.model.data']
        if self._context is None:
            self._context = {}
        model_data_ids = mod_obj.search([('model', '=', 'ir.ui.view'),
                                         ('name', '=',
                                          'view_hotel_reservation_form')])
        resource_id = model_data_ids.read(fields=['res_id'])[0]['res_id']
        return {'name': _('Reconcile Write-Off'),
                'context': self._context,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'hotel.reservation',
                'views': [(resource_id, 'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
                }
#

    @api.model
    def default_get(self, fields):
        """
        To get default values for the object.
        @param self: The object pointer.
        @param fields: List of fields for which we want default values
        @return: A dictionary which of fields with values.
        """
        if self._context is None:
            self._context = {}
        res = super(RoomReservationSummary, self).default_get(fields)
        # Added default datetime as today and date to as today + 30.
        from_dt = datetime.today()
        dt_from = from_dt.strftime(dt)
        to_dt = from_dt + relativedelta(days=30)
        dt_to = to_dt.strftime(dt)
        res.update({'date_from': dt_from, 'date_to': dt_to})

        if not self.date_from and self.date_to:
            date_today = datetime.datetime.today()
            first_day = datetime.datetime(date_today.year,
                                          date_today.month, 1, 0, 0, 0)
            first_temp_day = first_day + relativedelta(months=1)
            last_temp_day = first_temp_day - relativedelta(days=1)
            last_day = datetime.datetime(last_temp_day.year,
                                         last_temp_day.month,
                                         last_temp_day.day, 23, 59, 59)
            date_froms = first_day.strftime(dt)
            date_ends = last_day.strftime(dt)
            res.update({'date_from': date_froms, 'date_to': date_ends})
        return res

    # @api.onchange('date_from', 'date_to')
    # def get_room_summary(self):
    #     '''
    #     @param self: object pointer
    #      '''
    #     res = {}
    #     all_detail = []
    #     room_obj = self.env['hotel.room']
    #     reservation_line_obj = self.env['hotel.room.reservation.line']
    #     folio_room_line_obj = self.env['folio.room.line']
    #     user_obj = self.env['res.users']
    #     date_range_list = []
    #     main_header = []
    #     summary_header_list = ['Rooms']
    #     if self.date_from and self.date_to:
    #         if self.date_from > self.date_to:
    #             raise except_orm(_('User Error!'),
    #                              _('Please Check Time period Date \
    #                                   From can\'t be greater than Date To !'))
    #         if self._context.get('tz', False):
    #             timezone = pytz.timezone(self._context.get('tz', False))
    #         else:
    #             timezone = pytz.timezone('UTC')
    #         d_frm_obj = datetime.strptime(self.date_from, dt) \
    #             .replace(tzinfo=pytz.timezone('UTC')).astimezone(timezone)
    #         d_to_obj = datetime.strptime(self.date_to, dt) \
    #             .replace(tzinfo=pytz.timezone('UTC')).astimezone(timezone)
    #         temp_date = d_frm_obj
    #         while (temp_date <= d_to_obj):
    #             val = ''
    #             val = (str(temp_date.strftime("%a")) + ' ' +
    #                    str(temp_date.strftime("%b")) + ' ' +
    #                    str(temp_date.strftime("%d")))
    #             summary_header_list.append(val)
    #             date_range_list.append(temp_date.strftime
    #                                    (dt))
    #             temp_date = temp_date + timedelta(days=1)
    #         all_detail.append(summary_header_list)
    #         room_ids = room_obj.search([])
    #         all_room_detail = []
    #         for room in room_ids:
    #             room_detail = {}
    #             room_list_stats = []
    #             room_detail.update({'name': room.name or ''})
    #             if not room.room_reservation_line_ids and \
    #                     not room.room_line_ids:
    #                 for chk_date in date_range_list:
    #                     room_list_stats.append({'state': 'Free',
    #                                             'date': chk_date,
    #                                             'room_ids': room.id})
    #             else:
    #                 for chk_date in date_range_list:
    #                     ch_dt = chk_date[:10] + ' 23:59:59'
    #                     ttime = datetime.strptime(ch_dt, dt)
    #                     c = ttime.replace(tzinfo=timezone). \
    #                         astimezone(pytz.timezone('UTC'))
    #                     chk_date = c.strftime(dt)
    #                     reserline_ids = room.room_reservation_line_ids.ids
    #                     reservline_ids = (reservation_line_obj.search
    #                                       ([('id', 'in', reserline_ids),
    #                                         ('check_in', '<=', chk_date),
    #                                         ('check_out', '>=', chk_date),
    #                                         ('state', '=', 'assigned')
    #                                         ]))
    #                     if not reservline_ids:
    #                         sdt = dt
    #                         chk_date = datetime.strptime(chk_date, sdt)
    #                         chk_date = datetime. \
    #                             strftime(chk_date - timedelta(days=1), sdt)
    #                         reservline_ids = (reservation_line_obj.search
    #                                           ([('id', 'in', reserline_ids),
    #                                             ('check_in', '<=', chk_date),
    #                                             ('check_out', '>=', chk_date),
    #                                             ('state', '=', 'assigned')]))
    #                         for res_room in reservline_ids:
    #                             rrci = res_room.check_in
    #                             rrco = res_room.check_out
    #                             cid = datetime.strptime(rrci, dt)
    #                             cod = datetime.strptime(rrco, dt)
    #                             dur = cod - cid
    #                             if room_list_stats:
    #                                 count = 0
    #                                 for rlist in room_list_stats:
    #                                     cidst = datetime.strftime(cid, dt)
    #                                     codst = datetime.strftime(cod, dt)
    #                                     rm_id = res_room.room_id.id
    #                                     ci = rlist.get('date') >= cidst
    #                                     co = rlist.get('date') <= codst
    #                                     rm = rlist.get('room_id') == rm_id
    #                                     st = rlist.get('state') == 'Reserved'
    #                                     if ci and co and rm and st:
    #                                         count += 1
    #                                 if count - dur.days == 0:
    #                                     c_id1 = user_obj.browse(self._uid)
    #                                     c_id = c_id1.company_id
    #                                     con_add = 0
    #                                     amin = 0.0
    #                                     if c_id:
    #                                         con_add = c_id.additional_hours
    #                                     #                                        When configured_addition_hours is
    #                                     #                                        greater than zero then we calculate
    #                                     #                                        additional minutes
    #                                     if con_add > 0:
    #                                         amin = abs(con_add * 60)
    #                                     hr_dur = abs((dur.seconds / 60))
    #                                     #                                        When additional minutes is greater
    #                                     #                                        than zero then check duration with
    #                                     #                                        extra minutes and give the room
    #                                     #                                        reservation status is reserved or
    #                                     #                                        free
    #                                     if amin > 0:
    #                                         if hr_dur >= amin:
    #                                             reservline_ids = True
    #                                         else:
    #                                             reservline_ids = False
    #                                     else:
    #                                         if hr_dur > 0:
    #                                             reservline_ids = True
    #                                         else:
    #                                             reservline_ids = False
    #                                 else:
    #                                     reservline_ids = False
    #                     fol_room_line_ids = room.room_line_ids.ids
    #                     chk_state = ['draft', 'cancel']
    #                     folio_resrv_ids = (folio_room_line_obj.search
    #                                        ([('id', 'in', fol_room_line_ids),
    #                                          ('check_in', '<=', chk_date),
    #                                          ('check_out', '>=', chk_date),
    #                                          ('status', 'not in', chk_state)
    #                                          ]))
    #                     if reservline_ids or folio_resrv_ids:
    #                         room_list_stats.append({'state': 'Reserved',
    #                                                 'date': chk_date,
    #                                                 'room_ids': room.id,
    #                                                 'is_draft': 'No',
    #                                                 'data_model': '',
    #                                                 'data_id': 0})
    #                     else:
    #                         room_list_stats.append({'state': 'Free',
    #                                                 'date': chk_date,
    #                                                 'room_ids': room.id})
    #
    #             room_detail.update({'value': room_list_stats})
    #             all_room_detail.append(room_detail)
    #         main_header.append({'header': summary_header_list})
    #         self.summary_header = str(main_header)
    #         self.room_summary = str(all_room_detail)
    #     return res
#
    @api.onchange('check_out', 'check_in')
    def on_change_check_out(self):
        '''
        When you change checkout or checkin it will check whether
        Checkout date should be greater than Checkin date
        and update dummy field
        -----------------------------------------------------------
        @param self: object pointer
        @return: raise warning depending on the validation
        '''
        if self.check_out and self.check_in:
            if self.check_out < self.check_in:
                raise except_orm(_('Warning'),
                                 _('Checkout date should be greater \
                                    than Checkin date.'))

            @api.model
            def default_get(self, fields):
                """
                To get default values for the object.
                @param self: The object pointer.
                @param fields: List of fields for which we want default values
                @return: A dictionary which of fields with values.
                """
                if self._context is None:
                    self._context = {}
                res = super(QuickRoomReservation, self).default_get(fields)
                if self._context:
                    keys = self._context.keys()
                    if 'date' in keys:
                        res.update({'check_in': self._context['date']})
                    if 'room_ids' in keys:
                        room_ids = self._context['room_ids']
                        res.update({'room_ids': int(room_ids)})
                return res
# #
class QuickRoomReservation(models.TransientModel):
    _name = 'quick.room.reservation'
    _description = 'Quick Room Reservation'

    # partner_id = fields.Many2one('res.partner', string="Customer",
    #                              required=True)
    check_in = fields.Datetime('Check In', required=True)
    check_out = fields.Datetime('Check Out', required=True)
    room_ids = fields.Many2one('hotel.room', 'Room', required=True)
    adults = fields.Integer('Adults', size=64)
# #

    @api.onchange('check_out', 'check_in')
    def on_change_check_out(self):
        '''
        When you change checkout or checkin it will check whether
        Checkout date should be greater than Checkin date
        and update dummy field
        -----------------------------------------------------------
        @param self: object pointer
        @return: raise warning depending on the validation
        '''
        if self.check_out and self.check_in:
            if self.check_out < self.check_in:
                raise except_orm(_('Warning'),
                                 _('Checkout date should be greater \
                                    than Checkin date.'))

            @api.model
            def default_get(self, fields):
                """
                To get default values for the object.
                @param self: The object pointer.
                @param fields: List of fields for which we want default values
                @return: A dictionary which of fields with values.
                """
                if self._context is None:
                    self._context = {}
                res = super(QuickRoomReservation, self).default_get(fields)
                if self._context:
                    keys = self._context.keys()
                    if 'date' in keys:
                        res.update({'check_in': self._context['date']})
                    if 'room_id' in keys:
                        room_ids = self._context['room_ids']
                        res.update({'room_ids': int(roomid)})
                return res
# #

# class FolioRoomLine(models.Model):
#     _name = 'folio.room.line'
#     _description = 'Hotel Room Reservation'
#     _rec_name = 'room_ids'
#
#     room_ids = fields.Many2one('hotel.room', string='Room id')
#     check_in = fields.Datetime('Check In Date', required=True)
#     check_out = fields.Datetime('Check Out Date', required=True)
#     folio_id = fields.Many2one('hotel.folio', string='Folio Number')
# # # #
# class HotelFolio(models.Model):
#     _name = 'hotel.folio'
#     _description = 'hotel folio new'
#
#     reservation_id = fields.Many2one('hotel.reservation',
#                                      string='Reservation Id')
#     name = fields.Char('Folio Number', readonly=True, index=True,
#                        default='New')
#     # order_id = fields.Many2one('sale.order', 'Order', delegate=True,
#     #                            required=True, ondelete='cascade')
#     checkin_date = fields.Datetime('Check In', required=True, readonly=True,
#                                    states={'draft': [('readonly', False)]},
#                                    default=_get_checkin_date)
#     checkout_date = fields.Datetime('Check Out', required=True, readonly=True,
#                                     states={'draft': [('readonly', False)]},
#                                     default=_get_checkout_date)
#     room_lines = fields.One2many('hotel.folio.line', 'folio_id',
#                                  readonly=True,
#                                  states={'draft': [('readonly', False)],
#                                          'sent': [('readonly', False)]},
#                                  help="Hotel room reservation detail.")
#     # service_lines = fields.One2many('hotel.service.line', 'folio_id',
#     #                                 readonly=True,
#     #                                 states={'draft': [('readonly', False)],
#     #                                         'sent': [('readonly', False)]},
#     #                                 help="Hotel services detail provide to"
#     #                                      "customer and it will include in "
#     #                                      "main Invoice.")
#     # hotel_policy = fields.Selection([('prepaid', 'On Booking'),
#     #                                  ('manual', 'On Check In'),
#     #                                  ('picking', 'On Checkout')],
#     #                                 'Hotel Policy', default='manual',
#     #                                 help="Hotel policy for payment that "
#     #                                      "either the guest has to payment at "
#     #                                      "booking time or check-in "
#     #                                      "check-out time.")
#     duration = fields.Float('Duration in Days',
#                             help="Number of days which will automatically "
#                                  "count from the check-in and check-out date. ")
#     # currrency_ids = fields.One2many('currency.exchange', 'folio_no',
#     #                                 readonly=True)
#     # hotel_invoice_id = fields.Many2one('account.invoice', 'Invoice',
#     #                                    copy=False)
#     duration_dummy = fields.Float('Duration Dummy')
#
#     @api.model
#     def name_search(self, name='', args=None, operator='ilike', limit=100):
#         if args is None:
#             args = []
#         args += ([('name', operator, name)])
#         mids = self.search(args, limit=100)
#         return mids.name_get()
#
#     @api.model
#     def _needaction_count(self, domain=None):
#         """
#          Show a count of draft state folio on the menu badge.
#          @param self: object pointer
#         """
#         return self.search_count([('state', '=', 'draft')])
#
#     @api.model
#     def _get_checkin_date(self):
#         if self._context.get('tz'):
#             to_zone = self._context.get('tz')
#         else:
#             to_zone = 'UTC'
#         return _offset_format_timestamp1(time.strftime("%Y-%m-%d 12:00:00"),
#                                          DEFAULT_SERVER_DATETIME_FORMAT,
#                                          DEFAULT_SERVER_DATETIME_FORMAT,
#                                          ignore_unparsable_time=True,
#                                          context={'tz': to_zone})
#
#     @api.model
#     def _get_checkout_date(self):
#         if self._context.get('tz'):
#             to_zone = self._context.get('tz')
#         else:
#             to_zone = 'UTC'
#         tm_delta = datetime.timedelta(days=1)
#         return datetime.datetime.strptime(_offset_format_timestamp1
#                                           (time.strftime("%Y-%m-%d 12:00:00"),
#                                            DEFAULT_SERVER_DATETIME_FORMAT,
#                                            DEFAULT_SERVER_DATETIME_FORMAT,
#                                            ignore_unparsable_time=True,
#                                            context={'tz': to_zone}),
#                                           '%Y-%m-%d %H:%M:%S') + tm_delta
#
#     @api.multi
#     def copy(self, default=None):
#         '''
#         @param self: object pointer
#         @param default: dict of default values to be set
#         '''
#         return super(HotelFolio, self).copy(default=default)
#
#
# class HotelFolioLine(models.Model):
#     _name = 'hotel.folio.line'
#     _description = 'hotel folio1 room line'
#
#     # order_line_id = fields.Many2one('sale.order.line', string='Order Line',
#     #                                 required=True, delegate=True,
#     #                                 ondelete='cascade')
#     folio_id = fields.Many2one('hotel.folio', string='Folio',
#                                )
#     checkin_date = fields.Datetime('Check In', required=True,
#                                    default=_get_checkin_date)
#     checkout_date = fields.Datetime('Check Out', required=True,
#                                     default=_get_checkout_date)
#     is_reserved = fields.Boolean('Is Reserved',
#                                  help='True when folio line created from \
#                                     Reservation')
#
#     @api.multi
#     def copy(self, default=None):
#         '''
#         @param self: object pointer
#         @param default: dict of default values to be set
#         '''
#         return super(HotelFolioLine, self).copy(default=default)
#
#     @api.model
#     def _get_checkin_date(self):
#         if 'checkin' in self._context:
#             return self._context['checkin']
#         return time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
#
#     @api.model
#     def _get_checkout_date(self):
#         if 'checkout' in self._context:
#             return self._context['checkout']
#         return time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
#
#         @api.model
#         def create(self, vals, check=True):
#             """
#             Overrides orm create method.
#             @param self: The object pointer
#             @param vals: dictionary of fields value.
#             @return: new record set for hotel folio line.
#             """
#             if 'folio_id' in vals:
#                 folio = self.env["hotel.folio"].browse(vals['folio_id'])
#                 vals.update({'order_id': folio.order_id.id})
#             return super(HotelFolioLine, self).create(vals)
#
#         @api.constrains('checkin_date', 'checkout_date')
#         def check_dates(self):
#             '''
#             This method is used to validate the checkin_date and checkout_date.
#             -------------------------------------------------------------------
#             @param self: object pointer
#             @return: raise warning depending on the validation
#             '''
#             if self.checkin_date >= self.checkout_date:
#                 raise ValidationError(_('Room line Check In Date Should be \
#                        less than the Check Out Date!'))
#             if self.folio_id.date_order and self.checkin_date:
#                 if self.checkin_date <= self.folio_id.date_order:
#                     raise ValidationError(_('Room line check in date should be \
#                        greater than the current date.'))