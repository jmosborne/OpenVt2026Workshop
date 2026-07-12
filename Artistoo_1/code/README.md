# Sorting implementation in artistoo


## Quick start

If you are using conda (recommended), set up your environment so you have Nodejs. Navigate to the artistoo/code folder,
then create the conda environment:

```
conda env create -f env.yml
```

and activate it:


```
conda activate artistoo
```

install node packages (locally):

```
npm install
```

and get the artistoo library:

```
curl --output artistoo-cjs-v1.2.0.js "https://cdn.jsdelivr.net/gh/ingewortel/artistoo@1.2.0/build/artistoo-cjs.js"
```

now run a simulation and save the output:

```
node run-Cellsorting.js > ../data/sort.csv
```

Images will pop up in "img".

If not using conda, read on.

## Without conda


### Make and other command line tools:

To use all code, the easiest way to interact with the code is to use the Makefile.
Make sure you have basic command line tools such as 
"make", "awk", "bc" etc. On MacOS, look for xcode CLT. On Linux, look for build-essential. 
On Windows, I am not sure, but you can still run the code manually.

Other tools you may need:
- sed (used to automatically parse input json files for some of the exps)
- ffmpeg (if you want to make videos, see [this page](https://www.ffmpeg.org/download.html) 

### Nodejs, npm, and packages

You'll need Nodejs and its package manager to run Artistoo simulations from the command line. 
See (https://nodejs.org/en/download/)[https://nodejs.org/en/download/].

Standard package managers sometimes install incompatible versions of npm and nodejs. 
To avoid this, you can install both at once using nvm:

```
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
nvm install --lts
nvm use --lts
```

Once node and npm are installed, you can install the necessary packages locally using 

```
npm install
```

Then download the artistoo library script:

```
curl --output artistoo-cjs-v1.2.0.js "https://cdn.jsdelivr.net/gh/ingewortel/artistoo@1.2.0/build/artistoo-cjs.js"
```

and run

```
node run-Cellsorting.js > ../data/sort.csv
```

Images will pop up in "img".
