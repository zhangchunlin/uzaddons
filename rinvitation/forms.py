from uliweb.form import *
from uliweb.i18n import ugettext as _
from uliweb.orm import get_model
from uliweb import settings

class RegisterForm(Form):
    form_buttons = Submit(value=_('Register'), _class="btn btn-primary")
    #form_title = _('Register')
    
    username = StringField(label=_('Username'), required=True)
    password = PasswordField(label=_('Password'), required=True)
    password1 = PasswordField(label=_('Password again'), required=True)
    email = StringField(label=_('Email') ,html_attrs={"readonly":"readonly"}, required=True)
    icode = StringField(label=_('Invitation code'), html_attrs={"readonly":"readonly"}, required=True)
    vnote = StringField(label=_('Verification note'), html_attrs={"readonly":"readonly"}, required=True)
    next = HiddenField()
    
    def validate_username(self, data):
        from uliweb.orm import get_model
        
        if len(data)<settings.REGISTER.MIN_USERNAME_LEN:
            return _('User name too short,should >')+str(settings.REGISTER.MIN_USERNAME_LEN)
        
        if type(data)!=type(u""):
            udata = data.decode(settings.GLOBAL.HTMLPAGE_ENCODING)
        else:
            udata = data
        for w in settings.REGISTER.USERNAME_FORBIDDEN_WORDS:
            if udata.lower().find(w)!=-1:
                return unicode(_('User name should not contain: '))+'"%s"'%(unicode(w))
        
        User = get_model('user')
        user = User.get(User.c.username==data)
        if user:
            return _('User "%s" is already existed!') % data
    
    def form_validate(self, all_data):
        if len(all_data.password)<settings.REGISTER.MIN_PASSWORD_LEN:
            return {'password' : _('Password too short,should >')+str(settings.REGISTER.MIN_PASSWORD_LEN)}
        if all_data.password != all_data.password1:
            return {'password1' : _('Passwords are not match.')}

class IcodeForm(Form):
    form_buttons = Submit(value=_('Go to register'), _class="btn btn-primary")
    icode = StringField(label=_('Invitation code'), required=True)
    
    def form_validate(self,all_data):
        code = all_data.icode
        Icode = get_model("icode")
        icode = Icode.get(Icode.c.code==code)
        
        if not icode:
            return {'icode' : _('Invalid invitation code')}
        
        User = get_model("user")
        user = User.get(User.c.email==icode.email)
        
        if icode.used or user:
            return {'icode':_('This code has been used')}
