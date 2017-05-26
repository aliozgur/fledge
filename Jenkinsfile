node {
    def all_choice = 'all'
    def doc_choice = 'doc-tests'
    def py_choice = 'py-tests'
    def single_choice = 'single-test'

    // adding job parameters within jenkinsfile
    properties([
     parameters([
       stringParam(
         defaultValue: 'git@github.com:foglamp/FogLAMP.git',
         description: 'Repository which you want to use in this (upstream) job',
         name: 'repo_url'
       ),
       stringParam(
         defaultValue: 'fogl-67-ashish',
         description: 'The git branch you would like to build with.',
         name: 'branch'
       ),
       choice(
         choices: "${all_choice}\n${doc_choice}\n${py_choice}\n${single_choice}",
         description: "run tests as per your choice",
         name: 'suite'
       ),
       stringParam(
         defaultValue: 'tests/test_db_config.py',
         description: "If you want to run a particular test, for example 'tests/test_db_config.py'. You have to enter path for that test",
         name: 'single_test'
       )
     ])
])

  stage ("Clean Workspace"){
        // Delete workspace
        deleteDir()
    }

    stage ("Install Build"){
        // Git repo_url and branch params needed to clone
        checkout([$class: 'GitSCM', branches: [[name: "${branch}"]], doGenerateSubmoduleConfigurations: false, extensions: [[$class: 'CheckoutOption', timeout: 20], [$class: 'CloneOption', depth: 0, noTags: false, reference: '', shallow: true, timeout: 20]], submoduleCfg: [], userRemoteConfigs: [[credentialsId: 'jenkins', refspec: "+refs/heads/${branch}:refs/remotes/origin/${branch}", url: '${repo_url}']]])
    }
    
    stage ("Lint"){
        dir ('src/python/') {
            sh "pylint --generate-rcfile > pylint.cfg"
            sh 'pylint --rcfile=pylint.cfg $(find . -maxdepth 1 -name "*.py" -print)  --msg-template="{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}" > pylint.log || exit 0'
            warnings([canComputeNew:false, canResolveRelativePaths:false, defaultEncoding: '', excludePattern: '', healthy: '', includePattern: '', messagesPattern: '', parserConfigurations:[[parserName: 'PyLint', pattern: 'pylint.log']], unHealthy: ''])
        }
    }
    
    def gitBranch = branch.trim()
    def gitCommit = sh(returnStdout: true, script: 'git rev-parse HEAD').trim()
    def workspace_dir = sh(returnStdout: true, script: 'pwd').trim()

    ansiColor('xterm'){
        echo "git branch is ${gitBranch}"
        echo "git commit is $gitCommit"
        echo "Workspace is ${workspace_dir}"
    }
    stage ("Run tests and report"){
        dir ('src/python/') { 
            sh "pip3 install virtualenv"
            ansiColor('css'){
                echo "--- setting the virtualenv ---"
            }
            sh "virtualenv fogenv"
            sh "source fogenv/bin/activate"
            try{
                if (suite == "${all_choice}"){
                    ansiColor('css'){
                        echo "All tests"
                    }
                    sh "tox"
                }else if (suite == "${py_choice}"){
                    ansiColor('css'){
                        echo "Py tests"
                    }
                    sh "tox -e py35"
                }else if (suite == "${doc_choice}"){
                    ansiColor('css'){
                        echo "DOC tests"
                    }
                    sh "tox -e docs"
                }else if (suite == "${single_choice}"){
                        ansiColor('css'){
                            echo "Single test path is ${single_test}"
                        }
                        if(single_test == ''){
                            error 'Specify single_test parameter blank if you specify single-test as suite parameter'
                        }
                        // TODO: Need to find a way to run with tox
                        ansiColor('css'){
                            echo "--- installing requirements ---"
                        }
                        sh "pip3 install -r requirements.txt"
                        sh "pip3 install -e ."
                        sh "pytest $single_test --alluredir=allure/reports"
                        sh "pip3 uninstall FogLAMP <<< y"
                }
            }finally{
                stage ("Allure-Report"){
                    if (suite == "${doc_choice}" || suite == "${all_choice}"){
                        dir("../../docs/"){
                            allure([includeProperties: false, jdk: '', properties: [], reportBuildPolicy: 'ALWAYS', results: [[path: 'allure/reports']]])
                        }
                    if (suite == "${all_choice}"){
                        allure([includeProperties: false, jdk: '', properties: [], reportBuildPolicy: 'ALWAYS', results: [[path: 'allure/reports']]])
                    }
                    return;
                    }else if (suite == "${single_choice}"){
                        ansiColor('xterm'){
                            echo "--- generating allure report  ---"
                            sh "allure generate allure/reports"
                            echo "--- removing directory fogenv virtualenv ---"
                            sh "rm -rf fogenv/"
                        }
                    }
                    allure([includeProperties: false, jdk: '', properties: [], reportBuildPolicy: 'ALWAYS', results: [[path: 'allure/reports']]])
                }
            }    
        }
    }
}