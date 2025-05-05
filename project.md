


- go to next page adn get number result, done 

- refactor go to captcha solver, pre processing and post processing (so captcha solver is reusable), done 

- create test for captcha solver (with url directly), done 

- implement concurrency options, done 

- solve captcha without having to go to captcha page : extra captcha prams, provide them to solver and produce token, 
before : use selenium abse to go to page or provide url, sovle captcha, then handle output with slenium base
after: extract captcha params, send them to solver, receive token 
main module flow : 

1- go to captcha page and extract params 
2- replicate captcha 
3- solve captcha, return token 

main module: receive captcha params, replcate captcha, solve captcha 
helper modules: extract captcha params. submit captcha with token 

- test with webshare proxy / test with proxy control mobile proxy 

- send request with captcha token instead of going to next page 
- add lnnte usecase 