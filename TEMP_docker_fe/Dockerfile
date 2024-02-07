FROM node:lts-alpine

# install simple http server for serving static content
RUN npm install -g serve

# make the 'app' folder the current working directory
WORKDIR /app

# copy both 'package.json' and 'package-lock.json' (if available)
COPY package*.json ./

# install project dependencies
RUN npm install

# copy project files and folders to the current working directory (i.e. 'app' folder)
COPY . .

# build app for production with minification
RUN npm run build

EXPOSE 3000

CMD [ "serve", "-l", "3000", "./dist", "-s"]

