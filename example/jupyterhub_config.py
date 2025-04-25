c = get_config()

c.Authenticator.allowed_users = [
    'instructor1',
    'instructor2',
    'student1',
    'student2',
    'grader-course101',
    'grader-course123',
]

c.JupyterHub.load_groups = {
    'instructors': [
        'instructor1',
        'instructor2',
    ],
    'formgrade-course101': [
        'instructor1',
        'instructor2',
        'grader-course101',
    ],
    'formgrade-course123': [
        'instructor2',
        'grader-course123',
    ],
    'nbgrader-course101': [
        'instructor1',
        'instructor2',
        'student1',
    ],
    'nbgrader-course123': [
        'instructor2',
        'student1',
        'student2',
    ],
}

c.JupyterHub.load_roles = roles = [
    {
        'name': 'instructor',
        'groups': ['instructors'],
        'scopes': [
            'admin:users',
            'admin:servers',
        ],
    },
    {
        'name': 'server',
        'scopes': [
            'inherit',
        ],
    },
]
for course in ['course101', 'course123']:
    roles.append(
        {
            'name': f'formgrade-{course}',
            'groups': [f'formgrade-{course}'],
            'scopes': [
                f'access:services!service={course}',
            ],
        }
    )
    roles.append(
        {
            'name': f'nbgrader-{course}',
            'groups': [f'nbgrader-{course}'],
            'scopes': [
                'list:services',
                f'read:services!service={course}',
            ],
        }
    )


c.JupyterHub.services = [
    {
        'name': 'course101',
        'url': 'http://127.0.0.1:9999',
        'command': [
            'jupyterhub-singleuser',
            '--debug',
        ],
        'user': 'grader-course101',
        'cwd': '/home/grader-course101',
        'environment': {
            'JUPYTERHUB_DEFAULT_URL': '/lab'
        },
        'api_token': '{{course101_token}}',
    },
    {
        'name': 'course123',
        'url': 'http://127.0.0.1:9998',
        'command': [
            'jupyterhub-singleuser',
            '--debug',
        ],
        'user': 'grader-course123',
        'cwd': '/home/grader-course123',
        'environment': {
            'JUPYTERHUB_DEFAULT_URL': '/lab'
        },
        'api_token': '{{course123_token}}',
    },
]
