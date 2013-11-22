#coding=utf-8
import urllib
import random
import string

from uliweb import expose, decorators, functions, redirect
from uliweb.i18n import ugettext as _
from uliweb.orm import get_model

def register():
    from uliweb.contrib.auth import create_user, login
    print request.params
    form = functions.get_form('auth.RegisterForm')()
    
    if request.method == 'GET':
        form.next.data = request.GET.get('next', '/')
        form.icode.data = request.params.get('icode',None)
        if form.icode.data:
            Icode = get_model('icode')
            icode = Icode.get(Icode.c.code==form.icode.data)
            if icode:
                form.email.data = icode.email
            else:
                return redirect('/forum/icode')
        else:
            return redirect('/forum/icode')
        return {'form':form, 'msg':''}
    if request.method == 'POST':
        flag = form.validate(request.params)
        if flag:
            f, d = create_user(username=form.username.data, password=form.password.data)
            if f:
                #add auto login support 2012/03/23
                login(d)
                
                Icode = get_model('icode')
                icode = Icode.get(Icode.c.code==form.icode.data)
                icode.used = True
                icode.save()
                
                d.email = icode.email
                d.vnote = icode.vnote
                d.save()
                
                next = urllib.unquote(request.POST.get('next', '/'))
                return redirect(next)
            else:
                form.errors.update(d)
                
        msg = form.errors.get('_', '') or _('Register failed!')
        return {'form':form, 'msg':str(msg)}

@expose('/forum/icode')
def forum_icode():
    from forms import IcodeForm
    form = IcodeForm()
    if request.method == 'POST':
        flag = form.validate(request.params)
        if flag:
            return redirect('/register?icode=%s'%(form.icode.data))
    return {'form':form}

@expose('/api/icodes')
def api_icodes():
    if request.user.is_superuser:
        cpage = int(request.GET.get('cpage', 0))
        num1page = int(request.GET.get('num1page', 20))
        Icode = get_model('icode')
        num = Icode.all().count()
        pnum = (num+(num1page-1))/num1page
        icodes = Icode.all().order_by(Icode.c.id.desc()).offset(cpage*num1page).limit(num1page)
        l = [{"id":i.id,"code":i.code,"vnote":i.vnote,"used":i.used,"email":i.email}for i in list(icodes)]
        return json({'pnum':pnum,'list':l})
    else:
        return json([])

def gen_random_code(clen=20):
    random.seed()
    chars=string.ascii_letters+string.digits
    return ''.join([random.choice(chars) for i in range(clen)])

@expose('/api/add_icode')
def api_add_icode():
    from uliweb.mail import Mail
    
    msg = ""
    errmsg = ""
    retcode = -1
    if request.user.is_superuser:
        email =  request.POST.get("email","")
        vnote = request.POST.get("vnote","")
        if email and vnote:
            Icode = get_model('icode')
            if Icode.get(Icode.c.email==email):
                errmsg = _("Error: already generate code for this email address!")
            else:
                for i in xrange(10):
                    code = gen_random_code()
                    if not Icode.get(Icode.c.code==code):
                        break
                icode = Icode(code=code,
                    vnote=vnote,
                    creator=request.user,
                    used=False,
                    email=email)
                def get_mail_content(ic):
                    msg = _("Welcome to ")+settings.LAYOUT.TITLE+"\r\n"
                    msg += _("You are invited as: ")+ic.vnote+"\r\n"
                    msg += _("Your invitation code is: ")+ic.code+"\r\n"
                    msg += _("Please visit this URL to register: ")+"%s/register?icode=%s"%(request.url_root,ic.code)+"\r\n"
                    return msg
                try:
                    Mail().send_mail(settings.MAIL.FROM_ADDR,email,"Invitation code of zhc.f1do.com",get_mail_content(icode))
                    msg = _("Invitation code has been generated and send to ")+email
                except Exception,e:
                    print e
                    msg = _("Invitation code has been generated")
                    errmsg = _("Mail sent fail,you can send it manually to ")+email
                icode.save()
                
                retcode = 0
    else:
        errmsg = _("Error: you have no permission")
    return json({"retcode":retcode,"msg":msg,"errmsg":errmsg})


@expose('/forum/admin/icode')
@decorators.check_role('superuser')
def forum_admin_icode():
    return {}
