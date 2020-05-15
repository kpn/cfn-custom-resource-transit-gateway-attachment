TARGET_TEMPLATE = 'template.packaged.yaml'

.PHONY: clean package

clean:
	rm -f ${TARGET_TEMPLATE}
	make -C ./src/ clean

package: 
	make -C ./src/ build
	aws cloudformation package --template custom-resource.yaml --s3-bucket ${S3_BUCKET} --output-template-file ${TARGET_TEMPLATE}
