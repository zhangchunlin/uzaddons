#! /usr/bin/env python
#coding=utf-8

from uliweb import expose, response, request, settings, functions
from uliweb.orm import get_model
from uliweb.utils.timesince import timesince

@expose('/forum')
class PForumView(object):
    def __init__(self):
        self.status = {
            'close':{True:'打开', False:'关闭'},
            'sticky':{True:'取消顶置', False:'顶置'},
            'essence':{True:'取消精华', False:'精华'},
            'delete':{True:'恢复', False:'删除'},
            'hidden':{True:'取消隐藏', False:'隐藏'},
            'email':{True:'取消邮件关注', False:'设置邮件关注'},
            'homepage':{True:'取消首页显示', False:'设置首页显示'},
            'enable_comment':{True:'设置禁止回复', False:'设置允许回复'},
        }
        self.model = get_model('forum')

    @expose('<int:id>')
    def forum_index(self, id):
        """
        显示某论坛页面
        """
        from uliweb.utils.generic import ListView
        from sqlalchemy.sql import and_
        import math
        
        response.template = "ForumView/forum_index.html"
        
        pageno = int(request.values.get('page', 1)) - 1
        rows_per_page=int(request.values.get('rows', settings.get_var('PARA/FORUM_INDEX_NUMS')))
        
        Topic = get_model('forumtopic')
        Forum = get_model('forum')
        User = get_model('user')
        forum = Forum.get(int(id))
        condition = Topic.c.forum == int(id)
        order_by = [Topic.c.sticky.desc(), Topic.c.last_reply_on.desc()]
        if not forum.managers.has(request.user):
            condition = (Topic.c.hidden==False) & condition
        
        filter = request.GET.get('filter', 'all')
        if filter == 'essence':
            condition = (Topic.c.essence==True) & condition
        elif filter == 'sticky':
            condition = (Topic.c.sticky==True) & condition
        term = request.GET.get('term', '')
        type = request.GET.get('type', '1')
        if term:
            if type == '1':     #查找主题
                condition = (Topic.c.subject.like('%'+term+'%')) & condition
            elif type == '2':   #查找用户名
                condition = and_(Topic.c.posted_by == User.c.id,
                    User.c.username.like('%' + term + '%') | User.c.nickname.like('%' + term + '%'),
                    ) & condition
            
        def created_on(value, obj):
            return value.strftime('%Y-%m-%d')
        
        def last_reply_on(value, obj):
            return timesince(value)
        
        def subject(value, obj):
            import cgi
            
            if obj.topic_type:
                _type = u'[%s]' % obj.get_display_value('topic_type')
            else:
                _type = ''
            s = ''
            if obj.sticky:
                s += u'<font color="red">[顶]</font>'
            if obj.hidden:
                s += u'<font color="red">[隐]</font>'
            if obj.closed:
                s += u'<font color="red">[关]</font>'
            if obj.essence:
                s += u'<font color="red">[精]</font>'
            if obj.homepage:
                s += u'<font color="red">[首]</font>'
            return _type+ '<a href="/forum/%d/%d">%s</a>' % (int(id), obj.id, cgi.escape(obj.subject)) + s
        
        fields_convert_map = {'created_on':created_on, 'subject':subject,
            'last_reply_on':last_reply_on}
        view = ListView(Topic, condition=condition, order_by=order_by,
            rows_per_page=rows_per_page, pageno=pageno,
            fields_convert_map=fields_convert_map)
        view.query()    #in order to get the total count
        objects = view.objects()
        pages = int(math.ceil(1.0*view.total/rows_per_page))
        return {'forum':forum, 'objects':objects, 'filter':filter, 'term':term, 
            'page':pageno+1, 'total':view.total, 'pages':pages,
            'pagination':functions.create_pagination(request.path+'?'+request.query_string, view.total, pageno+1, rows_per_page),
            'type':type, 'filter_name':dict(settings.get_var('PARA/FILTERS')).get(filter)}
    