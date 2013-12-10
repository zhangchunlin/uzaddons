#! /usr/bin/env python
#coding=utf-8

from uliweb import expose, request, settings, functions, get_endpoint, decorators
from uliweb.orm import get_model
from uliweb.utils.timesince import timesince
from plugs.forums.views import ForumView
from uliweb.orm import NotFound
from datetime import timedelta
from uliweb.utils import date
import uuid
from uliweb.i18n import ugettext_lazy as _


@expose('/forum', replace=True)
class PForumView(ForumView):
    @expose('<int:id>', name=get_endpoint(ForumView.forum_index), template='ForumView/forum_index.html')
    def forum_index(self, id):
        """
        显示某论坛页面
        """
        from uliweb.utils.generic import ListView
        from sqlalchemy.sql import and_
        import math
        
        pageno = int(request.values.get('page', 1)) - 1
        rows_per_page=int(request.values.get('rows', settings.get_var('PARA/FORUM_INDEX_NUMS')))
        
        Topic = get_model('forumtopic')
        Forum = get_model('forum')
        User = get_model('user')
        forum = Forum.get(int(id))
        
        if forum.private and (not request.user):
            flash(_("This forum is private,you should login to view."))
            return redirect("/login")
        
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
    
    @expose('<int:forum_id>/<int:topic_id>', name=get_endpoint(ForumView.topic_view), template='ForumView/topic_view.html')
    def topic_view(self, forum_id, topic_id):
        """
        显示某主题页面
        """
        from uliweb.utils.generic import ListView
        from uliweb import settings
        
        pageno = int(request.values.get('page', 1)) - 1
        rows_per_page=int(request.values.get('rows', settings.get_var('PARA/FORUM_PAGE_NUMS')))
        cur_page = request.values.get('page', 1)
        
        Post = get_model('forumpost')
        Topic = get_model('forumtopic')
        Forum = get_model('forum')
        topic = Topic.get(int(topic_id))
        forum = topic.forum
        
        if forum.private and (not request.user):
            flash(_("This forum is private,you should login to view."))
            return redirect("/login")
        
        condition = Post.c.topic == int(topic_id)
        condition1 = (Post.c.parent == None) & condition
        condition2 = (Post.c.parent != None) & condition
        order_by = [Post.c.floor]
        
        def created_on(value, obj):
            return date.to_local(value).strftime('%Y-%m-%d %H:%M:%S %Z')
        
        def content(value, obj):
            return self._get_post_content(obj)
        
        def username(value, obj):
            try:
                username = unicode(obj.posted_by)
            except NotFound:
                username = obj._posted_by_
            return username
        
        def userimage(value, obj):
            get_user_image = function('get_user_image')
            try:
                url = get_user_image(obj.posted_by)
            except NotFound:
                url = get_user_image()
            return url
        
        def actions(value, obj):
            if not request.user:
                return ''
            
            a = []
            is_manager = forum.managers.has(request.user)
            is_superuser = request.user.is_superuser
            if obj.floor == 1 and obj.parent == None:
                if is_superuser:
                    #超户可以隐藏
                    a.append('<a href="#" rel="%d" class="hidden">%s</a>' % (obj.id, self.status['hidden'][obj.topic.hidden]))
                #第一楼为主贴，可以允许关闭，顶置等操作
                if is_manager:
                    a.append('<a href="#" rel="%d" class="top">%s</a>' % (obj.id, self.status['sticky'][obj.topic.sticky]))
                    a.append('<a href="#" rel="%d" class="essence">%s</a>' % (obj.id, self.status['essence'][obj.topic.essence]))
                    #a.append('<a href="#" rel="%d" class="homepage">%s</a>' % (obj.id, self.status['homepage'][obj.topic.homepage]))
                if obj.posted_by.id == request.user.id and obj.created_on+timedelta(days=settings.get_var('PARA/FORUM_EDIT_DELAY'))>=date.now():
                    #作者在n天之内，则可以编辑
                    url = url_for(ForumView.edit_topic, forum_id=forum_id, topic_id=topic_id)
                    a.append('<a href="%s" rel="%d" class="edit">编辑</a>' % (url, obj.id))
                    #作者可以关闭主题
                    a.append('<a href="#" rel="%d" class="close_thread">%s</a>' % (obj.id, self.status['close'][obj.topic.closed]))
                    #作者可以关闭评论
                    a.append('<a href="#" rel="%d" class="enable_comment">%s</a>' % (obj.id, self.status['enable_comment'][obj.topic.enable_comment]))
                    
                #处理贴子转移,管理员可以转移
                if is_manager or request.user.is_superuser:
                    url = url_for(ForumView.move_topic, forum_id=forum_id, topic_id=topic_id)
                    a.append('<a href="%s" rel="%d" class="move_topic">移动主题</a>' % (url, obj.id))
            else:
                if obj.posted_by.id == request.user.id and obj.created_on+timedelta(days=settings.get_var('PARA/FORUM_EDIT_DELAY'))>=date.now():
                    #作者在n天之内，则可以编辑
                    url = url_for(ForumView.edit_post, forum_id=forum_id, topic_id=topic_id, post_id=obj.id) + '?page=' + str(cur_page)
                    a.append('<a href="%s" rel="%d" class="edit_post">编辑</a>' % (url, obj.id))
            
            try:
                obj.posted_by
                if obj.posted_by.id == request.user.id:
                    a.append('<a href="#" rel="%d" class="email">%s</a>' % (obj.id, self.status['email'][obj.reply_email]))
            except NotFound:
                obj.posted_by = None
                obj.save()
            #只有允许评论时能可以回复
            if topic.enable_comment:
                a.append('<a href="/forum/%d/%d/%d/new_reply?page=%d">回复该作者</a>' % (forum_id, topic_id, obj.id, int(cur_page)))
            return ' | '.join(a)
        
        def updated(value, obj):
            if obj.floor == 1 and obj.topic.updated_on and not obj.parent:
                return u'<div class="updated">由 %s 于 %s 更新</div>' % (obj.topic.modified_user.username, timesince(obj.topic.updated_on))
        
        def posted_by(value, obj):
            pby = obj.posted_by
            return u"%s (%s)"%(pby.username,pby.vnote)
        
        fields = ['topic', 'id', 'username', 'userimage', 'posted_by', 'content',
            'created_on', 'actions', 'floor', 'updated', 'parent',
            ]
        fields_convert_map = {'created_on':created_on, 'content':content,
            'username':username, 'userimage':userimage, 'actions':actions,
            'updated':updated,'posted_by':posted_by}
        #view1 为生成一级回复，即回复主题
        view1 = ListView(Post, fields=fields, condition=condition1, order_by=order_by,
            rows_per_page=rows_per_page, pageno=pageno,
            fields_convert_map=fields_convert_map)
        #view2 为生成二级乃至多级回复
        view2 = ListView(Post, fields=fields, condition=condition2, order_by=order_by,
            pagination=False,
            fields_convert_map=fields_convert_map)
        key = '__topicvisited__:forumtopic:%s:%s:%s' % (request.remote_addr, forum_id, topic_id)
        cache = function('get_cache')()
        v = cache.get(key, None)
        if not v:
            Topic.filter(Topic.c.id==int(topic_id)).update(num_views=Topic.c.num_views+1)
            cache.set(key, 1, settings.get_var('PARA/FORUM_USER_VISITED_TIMEOUT'))
        
        slug = uuid.uuid1().hex
        
        #处理posts和sub_posts
        query = view1.query()
        posts = []
        sub_posts = {}
        def process_sub(ids):
            _ids = []
            for x in Post.filter(Post.c.parent.in_(ids)).order_by(Post.c.floor):
                obj = view2.object(x)
                d = sub_posts.setdefault(str(x._parent_), [])
                d.append(obj)
                _ids.append(x.id)
            if _ids:
                process_sub(_ids)
                
        ids = []
        for row in query:
            posts.append(view1.object(row))
            ids.append(row.id)
            
        process_sub(ids)
           
        pagination = functions.create_pagination(request.path+'?'+request.query_string, view1.total,
            pageno+1, rows_per_page)
        return {'forum':forum, 'topic':topic, 'slug':slug, 
            'has_email':bool(request.user and request.user.email), 
            'page':pageno+1, 'pagination':pagination,
            'posts':posts, 'sub_posts':sub_posts}
    
    @expose('post_actions', name=get_endpoint(ForumView.post_actions))
    @decorators.check_role('trusted')
    def post_actions(self):
        Post = get_model('forumpost')
        
        action = request.POST.get('action')
        post_id = request.POST.get('post_id')
        
        post = Post.get(int(post_id))
        if not post:
            return json({'msg':"没找到对应的发贴"})
        topic = post.topic
        flag = False
        topic_flag = False
        txt = ''
        msg = '处理成功'
        #topic
        is_manager = post.topic.forum.managers.has(request.user)
        is_post_owner = (post.posted_by.id == request.user.id)
        is_superuser = request.user.is_superuser
        if is_post_owner:
            if action == 'close_thread':
                topic.closed = not topic.closed
                topic_flag = True
                txt = self.status['close'][topic.closed]
            elif action == 'enable_comment':
                topic.enable_comment = not topic.enable_comment
                topic_flag = True
                txt = self.status['enable_comment'][topic.enable_comment]
        if is_superuser:
            if action == 'hidden':
                topic.hidden = not topic.hidden
                topic_flag = True
                txt = self.status['hidden'][topic.hidden]
        if is_manager:
            if action == 'top':
                topic.sticky = not topic.sticky
                topic_flag = True
                txt = self.status['sticky'][topic.sticky]
            elif action == 'essence':
                topic.essence = not topic.essence
                topic_flag = True
                txt = self.status['essence'][topic.essence]
            elif action == 'homepage':
                topic.homepage = not topic.homepage
                topic_flag = True
                txt = self.status['homepage'][topic.homepage]
            
        #post
        ok = False
        if is_post_owner:
            if action == 'email':
                post.reply_email = not post.reply_email
                flag = True
                txt = self.status['email'][post.reply_email]
                #检查用户邮箱是否存在
                if post.reply_email and not post.posted_by.email:
                    msg = '您的邮箱尚未设置，将无法处理邮件'
                
        if flag:
            post.save()
        if topic_flag:
            topic.save()
        if flag or topic_flag:
            return json({'msg':msg, 'txt':txt})
        else:
            return json({'msg':'命令未识别或无权限, 未做修改'})
    
