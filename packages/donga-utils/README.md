# @wijiseung04-blip/donga-utils

donga 프로젝트의 공용 유틸리티입니다. GitHub Packages(npm 레지스트리)로 배포됩니다.

## 설치

GitHub Packages의 npm 패키지는 공개 패키지라도 설치할 때 인증이 필요합니다.
`read:packages` 권한이 있는 토큰을 준비한 뒤 프로젝트에 `.npmrc`를 만듭니다.

```
@wijiseung04-blip:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=${GITHUB_TOKEN}
```

```bash
npm install @wijiseung04-blip/donga-utils
```

## 사용법

```js
const { greet } = require('@wijiseung04-blip/donga-utils');

greet();          // 'Hello, world!'
greet('  OSS ');  // 'Hello, OSS!'
```

## 배포

`donga-utils-v<버전>` 형식의 태그로 GitHub Release를 발행하면 `npm-publish.yml` 워크플로가 테스트 후 배포합니다.
태그 버전과 `package.json`의 `version`이 다르면 배포하지 않습니다.
