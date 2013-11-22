#! /usr/bin/env python
#coding=utf-8

from uliweb.orm import *


class Forum(Model):#论坛
    name = Field(str, verbose_name='论坛名称', max_length=100, required=True)
#    slug = models.SlugField(max_length = 110)#标签
    description = Field(TEXT, verbose_name='论坛描述')
    ordering = Field(int, verbose_name='排序',default = 1)
    category = Reference('forumcategory', verbose_name='所属板块', collection_name='forums', required=True)
    created_on = Field(datetime.datetime, verbose_name='创建时间', auto_now_add=True)
    updated_on = Field(datetime.datetime, verbose_name='修改时间', auto_now_add=True, auto_now=True)
    num_topics = Field(int, verbose_name='主题总数')
    num_posts = Field(int, verbose_name='文章总数')
#    attachments = Field(FILE, verbose_name='附件', hint='文件大小不能超过2M，请注意文件大小')

    last_reply_on = Field(datetime.datetime, verbose_name='最新回复时间', nullable=True)
    last_post_user = Reference('user', verbose_name='最后回复人', collection_name="last_post_user_forums", nullable=True)
    last_post = Field(int, verbose_name='最后发贴id', nullable=True)
    managers = ManyToMany('user', verbose_name='管理员')

    manager_only = Field(bool, verbose_name='是否只有管理员可以发贴')
    private = Field(bool, verbose_name='是否注册用户可见', nullable=True)
    
    def __unicode__(self):
        return self.name
    
    class AddForm:
        fields = ['name', 'description', 'ordering', 'managers', 'manager_only', 'private']
        
    class EditForm:
        fields = ['name', 'description', 'ordering', 'managers', 'manager_only', 'private']
    
    class Table:
        fields = [
            {'name':'name', 'width':200},
            {'name':'description', 'width':200},
            {'name':'category', 'width':100},
            {'name':'ordering', 'width':40},
            {'name':'managers', 'width':100},
            {'name':'topictype'},
            {'name': 'manager_only', 'width': 100},
            {'name': 'private', 'width': 40},
        ]

