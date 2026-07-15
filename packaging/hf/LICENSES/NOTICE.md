# Third-Party Notices

## DiffusionGemma

The quantized GGUF is derived from `google/diffusiongemma-26B-A4B-it`, whose
model card identifies the model license as Apache-2.0:

https://huggingface.co/google/diffusiongemma-26B-A4B-it

The derived model must retain the applicable license and attribution notices.
The full license text is included as `APACHE-2.0.txt`.

## CUDA runtime libraries

The package contains binary copies of `libcudart.so.13`, `libcublas.so.13`, and
`libcublasLt.so.13` in a private application runtime directory. These files are
listed as redistributable CUDA Toolkit components subject to the NVIDIA SDK and
CUDA Toolkit license terms:

https://docs.nvidia.com/cuda/eula/

The EULA shipped with CUDA 13.1 is included as `NVIDIA-CUDA-EULA.txt`.

## llama.cpp and other dependencies

The custom llama.cpp fork is distributed under the MIT license included as
`LLAMA-CPP-MIT.txt`. Retain all notices from its other dependencies. The
runtime is not endorsed by Google, NVIDIA, Hugging Face, or the upstream
llama.cpp project.
