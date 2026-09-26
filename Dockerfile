FROM public.ecr.aws/glue/aws-glue-libs:5
USER root
RUN pip install pyyaml
USER hadoop
