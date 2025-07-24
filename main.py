#!/usr/bin/python
# -*- coding: utf-8 -*-

from github import Github
from github.Issue import Issue
from github.Repository import Repository
import os
import time
import urllib.parse
import codecs
from nasa_client import NasaClient
from word_cloud import WordCloudGenerator

user: Github
username: str
ghiblog: Repository
cur_time: str


def format_issue(issue: Issue):
    return '- [%s](%s)  %s  \t \n' % (
        issue.title, issue.html_url, sup('%s :speech_balloon:' % issue.comments))


def sup(text: str):
    return '<sup>%s</sup>' % text


def sub(text: str):
    return '<sub>%s</sub>' % text


def update_readme_md_file(contents):
    with codecs.open('README.md', 'w', encoding='utf-8') as f:
        f.writelines(contents)
        f.flush()
        f.close()


def login():
    global user, username
    github_repo_env = os.environ.get('GITHUB_REPOSITORY')
    username = github_repo_env[0:github_repo_env.index('/')]
    password = os.environ.get('GITHUB_TOKEN')
    user = Github(username, password)


def get_ghiblog():
    global ghiblog
    ghiblog = user.get_repo(os.environ.get('GITHUB_REPOSITORY'))


def bundle_summary_section():
    global ghiblog
    global cur_time
    global user
    global username

    total_label_count = ghiblog.get_labels().totalCount
    total_issue_count = ghiblog.get_issues().totalCount

    pic_of_the_day = NasaClient().get_picture_of_the_day()

    summary_section = '''

<p align='center'>
    <img src="https://badgen.net/badge/labels/{1}"/>
    <img src="https://badgen.net/github/issues/{0}/ghiblog"/>
    <img src="https://badgen.net/badge/last-commit/{2}"/>
    <img src="https://badgen.net/github/forks/{0}/ghiblog"/>
    <img src="https://badgen.net/github/stars/{0}/ghiblog"/>
    <img src="https://badgen.net/github/watchers/{0}/ghiblog"/>
    <img src="https://badgen.net/github/release/{0}/ghiblog"/>
</p>

<p align='center'>
    <a href="https://github.com/jwenjian/visitor-count-badge">
        <img src="https://visitor-badge.glitch.me/badge?page_id=jwenjian.ghiblog"/>
    </a>
</p>

![Alt](https://repobeats.axiom.co/api/embed/621efcb9d6537f23aca93d700c66a832c574d6e0.svg)

'''.format(username, total_label_count, cur_time)

    return summary_section


def bundle_pinned_issues_section():
    global ghiblog
    pinned_label = ghiblog.get_label('置顶')
    if not pinned_label:
        return '\n## 置顶 :thumbsup: \n（暂无置顶文章）\n'

    pinned_issues = ghiblog.get_issues(labels=[pinned_label])

    pinned_issues_section = '\n## 置顶 :thumbsup: \n'
    for issue in pinned_issues:
        pinned_issues_section += format_issue(issue)

    return pinned_issues_section


def format_issue_with_labels(issue: Issue):
    global user, username

    labels = issue.get_labels()
    labels_str = ''

    for label in labels:
        labels_str += '[%s](https://github.com/%s/ghiblog/labels/%s), ' % (
            label.name, username, urllib.parse.quote(label.name))
    
    if issue.body:
        if '---' in issue.body:
            body_summary = issue.body[:issue.body.index('---')]
        else:
            body_summary = issue.body[:150]
    else:
       body_summary = '' 

    return '''
#### [{0}]({1}) {2} \t {3}

:label: : {4}

{5}

[更多>>>]({1})

---

'''.format(issue.title, issue.html_url, sup('%s :speech_balloon:' % issue.comments), 
           issue.created_at.strftime('%Y-%m-%d'), labels_str[:-2], body_summary)


def bundle_new_created_section():
    global ghiblog

    new_5_created_issues = ghiblog.get_issues()[:5]

    new_created_section = '## 最新 :new: \n'

    for issue in new_5_created_issues:
        new_created_section += format_issue_with_labels(issue)

    return new_created_section


def bundle_list_by_labels_section():
    global ghiblog
    all_labels = ghiblog.get_labels()

    if not all_labels:
        return "## 分类  :card_file_box: \n（暂无分类标签）"

    # 生成词云部分
    try:
        wordcloud_image_url = WordCloudGenerator(ghiblog).generate()
        wordcloud_section = f"""
<p align="center">
    <img src="{wordcloud_image_url}" alt="Issue词云" title="Issue词云" width="80%">
    <br>
    <sub>点击下方分类标签查看详细内容</sub>
</p>
"""
    except Exception as e:
        print(f"生成词云失败: {e}")
        wordcloud_section = ""

    list_by_labels_section = f"""
## 分类  :card_file_box: 

{wordcloud_section}

<details open="open">
<summary><b>点击展开/折叠分类</b></summary>
"""

    for label in all_labels:
        try:
            issues_in_label = ghiblog.get_issues(labels=[label])
            count = issues_in_label.totalCount
            temp = ""
            for issue in issues_in_label:
                temp += f"""
<div style="margin: 10px 0; padding: 10px; border-left: 3px solid #eee;">
{format_issue_with_labels(issue)}
</div>
"""
            
            list_by_labels_section += f"""
<details style="margin-bottom: 15px;">
<summary><b>{label.name}</b> <sup>{count}篇</sup></summary>
{temp}
</details>
"""
        except Exception as e:
            print(f"获取标签 '{label.name}' 的 Issues 失败: {e}")
            continue

    list_by_labels_section += "</details>"
    return list_by_labels_section


def bundle_cover_image_section() -> str:
    global ghiblog
    try:
        cover_label = ghiblog.get_label(':framed_picture:封面')
        if cover_label is None:
            return ''
            
        cover_issues = ghiblog.get_issues(labels=[cover_label])
        
        if cover_issues.totalCount == 0:
            return ''

        comments = cover_issues[0].get_comments()
        if comments.totalCount == 0:
            return ''

        last_comment = comments[comments.totalCount - 1]
        
        if '---' in last_comment.body:
            img_md, img_desc = last_comment.body.split('---', 1)
        else:
            img_md = last_comment.body
            img_desc = ''

        if not img_md or '(' not in img_md or ')' not in img_md:
            return ''

        img_url = img_md[img_md.index('(')+1:img_md.index(')')]
        
        return f'''
<p align='center'>
<a href='{last_comment.html_url}'>
<img src='{img_url}' width='50%' alt='{img_desc}'>
</a>
</p>
<p align='center'>
<span>{img_desc}</span>
</p>
'''
    except Exception as e:
        print(f"生成封面图片时出错: {e}")
        return ''


def bundle_projects_section() -> str:
    global ghiblog, username
    project_label = ghiblog.get_label('开源')
    if not project_label:
        return ''
    issues = ghiblog.get_issues(labels=[project_label])
    if not issues or issues.totalCount == 0:
        return ''
    content = ''
    for (idx, i) in enumerate(issues):
        content += '''
| [{1}](https://github.com/{0}/{1}) | {2} | ![](https://badgen.net/github/stars/{0}/{1}) ![](https://badgen.net/github/forks/{0}/{1}) ![](https://badgen.net/github/watchers/{0}/{1}) |'''.format(
            username, i.title, i.body)
        if idx == 0:
            content += '\n| --- | --- | --- |'
    return '''
# 开源项目

{}

'''.format(content)


def execute():
    global cur_time
    # common
    cur_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    # 1. login
    login()

    # 2. get ghiblog
    get_ghiblog()

    # 3. summary section
    summary_section = bundle_summary_section()
    print(summary_section)

    # 4. pinned issues section 
    pinned_issues_section = bundle_pinned_issues_section()
    print(pinned_issues_section)

    # 5. new created section
    new_created_section = bundle_new_created_section()
    print(new_created_section)

    # 6. list by labels section
    list_by_labels_section = bundle_list_by_labels_section()
    print(list_by_labels_section)

    # 7. cover image section
    cover_image_section = bundle_cover_image_section()
    print(cover_image_section)

    # 8. projects section
    projects_section = bundle_projects_section()
    print(projects_section)

    # 9. about me section
    # about_me_section = bundle_about_me_section()
    # print(about_me_section)

    # 合并所有内容
    contents = [
        summary_section,
        pinned_issues_section,
        new_created_section,
        list_by_labels_section,
        cover_image_section,
        projects_section
    ]
    update_readme_md_file(contents)

    print('README.md updated successfully!!!')


if __name__ == '__main__':
    execute()
