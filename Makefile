conda:
	cd ~/mlops-zoomcamp-project
	conda create --name py35 python=3.10
	conda activate mlops-project
	pip install -r requirements.txt

terraform:
	cd ~/mlops-zoomcamp-project/terraform
	terraform init
	terraform plan
	terraform apply

prefect:
	cd ~/mlops-zoomcamp-project
	conda activate prefect-env
	prefect deployment build prefect/main_flow.py:main -n Example_flow
	prefect deployment apply main-deployment.yaml
	prefect agent start -q 'default'

MLFlow:
	mlflow ui --host localhost:5000 --backend-store-uri sqlite:///mlflow.db