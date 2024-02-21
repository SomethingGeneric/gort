models:
	ollama create explaingen -f explaingen/Modelfile
	ollama create codegen -f codegen/Modelfile
	sudo systemctl restart ollama