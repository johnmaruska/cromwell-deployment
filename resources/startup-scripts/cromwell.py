#!/usr/bin/env python3

import os, subprocess, sys

CROMWELL_CLOUDSQL_PASSWORD='@CROMWELL_CLOUDSQL_PASSWORD@'
CROMWELL_VERSION='@CROMWELL_VERSION@'
CROMWELL_GCS_ROOT='@CROMWELL_GCS_ROOT@'
SERVICE_ACCOUNT_EMAIL='@SERVICE_ACCOUNT_EMAIL@'
PROJECT='@PROJECT@'

INSTALL_DIR = os.path.join(os.path.sep, 'opt', 'cromwell')
JAR_DIR = os.path.join(INSTALL_DIR, "jar")
CONFIG_DIR = os.path.join(INSTALL_DIR, "config")
GOOGLE_URL = "http://metadata.google.internal/computeMetadata/v1/instance/attributes"

def create_directories():
    print("Create directories...")
    for dn in (INSTALL_DIR, JAR_DIR, CONFIG_DIR):
        if not os.path.exists(dn):
            os.makedirs(dn)

def install_packages():
    print("Install pacakges...")

    packages = [
        'curl',
        'default-jdk',
        'default-mysql-client-core',
        'git',
        'python3-pip',
        'python3-dev',
        'python3-setuptools',
        'less',
        'vim',
        ]

    while subprocess.call(['apt-get', 'update']):
        print("Failed to apt-get update. Trying again in 5 seconds")
        time.sleep(5)

    while subprocess.call(['apt-get', 'install', '-y'] + packages):
        print("Failed to install packages with apt-get install. Trying again in 5 seconds")
        time.sleep(5)

    # Python deps
    import pip
    pip.main(["install", "jinja2", "pyyaml", "requests>=2.20.0"])

    print("Install pacakges...DONE")

#-- install_packages

def install_cromwell():
    #curl -OL https://github.com/broadinstitute/cromwell/releases/download/${VERSION}/cromwell-${VERSION}.jar && mv cromwell-${VERSION}.jar ${JAR_DIR}/
    #curl -OL https://github.com/broadinstitute/cromwell/releases/download/${VERSION}/womtool-${VERSION}.jar && mv womtool-${VERSION}.jar ${JAR_DIR}/
    print("Install cromwell and womtool...")
    import requests, yaml
    os.chdir(JAR_DIR)
    for name in "cromwell", "womtool":
        print("Install {} version {} ...".format(name, CROMWELL_VERSION))
        jar_fn = os.path.join(JAR_DIR, ".".join([name, "jar"]))
        if os.path.exists(jar_fn):
            print("Already installed at {} ...".format(jar_fn))
            continue
        url = "https://github.com/broadinstitute/cromwell/releases/download/{0}/{1}-{0}.jar".format(CROMWELL_VERSION, name)
        print("URL {}".format(url))
        response = requests.get(url)
        if not response.ok: raise Exception("GET failed for {}".format(url))
        print("Writing content to {}".format(jar_fn))
        with open(jar_fn, "wb") as f:
            f.write(response.content)

    print("Install cromwell...DONE")
#-- install_cromwell

def install_cromwell_config():
    #gsutil cp ${CONFIG} ${LCONFIG}
    #perl -p -i -e "s/cromwell-mysql:3306/${DB_NAME}:3306/g" ${LCONFIG}
    #DB_NAME=$(curl http://metadata.google.internal/computeMetadata/v1/instance/attributes/mysql-database-name -H "Metadata-Flavor: Google")
    fn = os.path.join(CONFIG_DIR, 'PAPI.v2.conf')
    if os.path.exists(fn):
        print("Already installed cromwell PAPI v2 config...SKIPPING")
        return
    sys.stderr.write("Install cromwell PAPI v2 config...")
    from jinja2 import Template
    papi_template = Template( _fetch_instance_info(name='papi-v2-conf') )
    ip = _fetch_instance_info(name='cloudsql-ip')
    params = { "ip": ip, "password": CROMWELL_CLOUDSQL_PASSWORD }
    with open(fn, 'w') as f:
        f.write( papi_template.render(cloudsql=params,
                                      project=PROJECT,
                                      service_account_email=SERVICE_ACCOUNT_EMAIL,
                                      cromwell_gcs_root=CROMWELL_GCS_ROOT) )
#-- install_cromwell_config

def install_cromshell():
    os.chdir("/opt")
    if os.path.exists("/opt/cromshell"):
        print("Already installed cromshell...SKIPPING")
        return
    cmd = ["git", "clone", "https://github.com/broadinstitute/cromshell.git"]
    print("RUNNING: {}".format(" ".join(cmd)))
    subprocess.check_call(cmd)
#-- install_cromshell

def add_and_start_cromwell_service():
    _fetch_and_save_instance_info(name='cromwell-service', fn=os.path.join(os.path.sep, 'etc', 'systemd', 'system', 'cromwell.service'))
    print("Start cromwell service...")
    subprocess.check_call(['systemctl', 'daemon-reload'])
    subprocess.check_call(['systemctl', 'start', 'cromwell'])
#-- add_cromwell_service

def _fetch_and_save_instance_info(name, fn):
    if os.path.exists(fn):
        print("Already installed {} to {} ... SKIPPING".format(name, fn))
        return
    print("Install {} ...".format(fn))
    content = _fetch_instance_info(name)
    with open(fn, 'w') as f:
        f.write(content)
#-- _fetch_and_save_instance_info

def _fetch_instance_info(name):
    import requests, yaml
    url = "/".join([GOOGLE_URL, name])
    response = requests.get(url, headers={'Metadata-Flavor': 'Google'})
    if not response.ok: raise Exception("GET failed for {}".format(url))
    return response.text
#-- _fetch_instance_info

if __name__ == '__main__':
    create_directories()
    install_packages()
    install_cromwell()
    install_cromwell_config()
    install_cromshell()
    add_and_start_cromwell_service()
    print("Startup script...DONE")
#-- __main__
