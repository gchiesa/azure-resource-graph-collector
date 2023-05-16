#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  deploy_function_app.py
#

import argparse
import logging
import os
import subprocess
import sys
import time


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Wrapper around azure CLI to deploy from Terraform."
    )
    parser.add_argument(
        "--root-dir",
        type=str,
        dest="root_dir",
        required=True,
        help="The root directory of the function app.",
    )
    parser.add_argument(
        "--function-dir",
        type=str,
        dest="function_dir",
        required=True,
        help="The directory where the function's app code resides.",
    )
    parser.add_argument(
        "--subscription",
        type=str,
        dest="subscription",
        required=True,
        help="The name of the Azure subscription.",
    )
    parser.add_argument(
        "--resource-group",
        type=str,
        dest="resource_group",
        required=True,
        help="The name of the Azure resource group.",
    )
    parser.add_argument(
        "--app-name",
        type=str,
        dest="app_name",
        required=True,
        help="The name of the Azure resource group.",
    )
    parser.add_argument(
        "--attempts",
        type=int,
        dest="attempts",
        default=10,
        help="The number of times to attempt redeployment.",
    )

    return parser.parse_args()


class DeployFunctionApp:
    def __init__(
        self, root_dir, function_dir, app_name, deployment_attempts, subscription, resource_group
    ):
        self.root_dir = root_dir
        self.function_dir = function_dir
        self.app_name = app_name
        self.deployment_attempts = deployment_attempts
        self.subscription = subscription
        self.resource_group = resource_group

        logging.basicConfig(
            format=f"%(asctime)s - %(levelname)s - {self.app_name} - %(message)s",
            level=logging.INFO,
        )

    def download_app_dependencies(self):
        logging.info(f"Downloading app dependencies.")
        python_packages = subprocess.run(
            [
                "python",
                "-m",
                "pip",
                "install",
                "--target",
                ".python_packages/lib/site-packages",
                "-r",
                "requirements.txt",
            ],
            cwd=self.root_dir,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

        if python_packages.returncode != 0:
            error_message = python_packages.stderr.decode().split("\n")[0]
            logging.error(
                f"Failed to install Python dependencies. Reason: {error_message}"
            )
            sys.exit(1)

    def create_app_package(self):
        logging.info(f"Creating app package.")
        package = subprocess.run(
            [
                "zip",
                "-r",
                f"{self.app_name}.zip",
                self.function_dir,
                "host.json",
                ".python_packages",
                "requirements.txt",
                "-x",
                "*__pycache__*",
                "-x",
                "*.pyc",
                "-x",
                "*.terra*"
            ],
            cwd=self.root_dir,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

        if package.returncode != 0:
            error_message = package.stderr.decode().split("\n")[0]
            logging.error(
                f"Failed to create app zip package. Reason: {error_message}"
            )
            sys.exit(1)

    def deploy_function_app(self):
        logging.info(f"Deploying app to Azure.")
        for attempt in range(1, self.deployment_attempts+1):
            deployment = subprocess.run(
                [
                    "az",
                    "functionapp",
                    "deployment",
                    "source",
                    "config-zip",
                    "--subscription",
                    self.subscription,
                    "-g",
                    self.resource_group,
                    "-n",
                    self.app_name,
                    "--src",
                    f"{self.app_name}.zip",
                ],
                cwd=self.root_dir,
                check=False,
                timeout=360,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )

            if deployment.returncode == 0:
                logging.info(
                    f"Finished deploying app to Azure on attempt {attempt}."
                )
                break
            else:
                error_message = deployment.stderr.decode().split("\n")[0]
                logging.error(
                    f"Failed to deploy app to Azure on attempt {attempt}. Retry. Reason: {error_message}"
                )
                time.sleep(3)
        else:
            logging.error(
                f"Failed to deploy app to Azure after {attempt} attempts. Giving up."
            )
            sys.exit(1)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        for location in [".python_packages", f"{self.app_name}.zip"]:
            try:
                os.remove(self.root_dir + "/" + location)
            except IsADirectoryError:
                os.system("rm -rf " + self.root_dir + "/" + location)
            except Exception:
                pass


def main():
    args = parse_arguments()
    with DeployFunctionApp(
        root_dir=args.root_dir,
        function_dir=args.function_dir,
        app_name=args.app_name,
        subscription=args.subscription,
        resource_group=args.resource_group,
        deployment_attempts=args.attempts,
    ) as deployment:
        deployment.download_app_dependencies()
        deployment.create_app_package()
        deployment.deploy_function_app()


if __name__ == "__main__":
    main()
