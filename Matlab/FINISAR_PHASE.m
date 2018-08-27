diary on;
%%
Dev = OpenFinisar3('WS4');
%%
NumPixels = ceil((Dev.StopF-Dev.StartF).*1000);
dim=NumPixels;
stepf=(Dev.StopF-Dev.StartF)/dim;
vectorf=(-dim/2:dim/2-1)*stepf;
z=0.03793; %    0.03797;%km 65%04042
beta2=21.612;
Phi2=z*beta2;
    beta3=0.01;%0.134;
Phi3=beta3*z;
beta4=-0.0006; %1.00;
Phi4=beta4*z;
    beta6=0.000;%15; %20.0;
Phi6=beta6*z;
pixelKoheras=6722; % Center line of the comb. 
center=pixelKoheras*stepf;
cs=center-dim*stepf/2;
Hw=exp(1i*Phi2/2*(2*pi*(vectorf-cs)).^2).*exp(1i*Phi3/6*(2*pi*(vectorf-cs)).^3).*exp(1i*Phi4/24*(2*pi*(vectorf-cs)).^4).*exp(1i*Phi6/720*(2*pi*(vectorf-cs)).^6);
fase=angle(Hw)+pi;
% amplitud=zeros(1,dim);
 amplitud(1,pixelKoheras+30*150:NumPixels)=1;
 amplitud=amplitud.*0+1;
  amplitud(1,pixelKoheras+5000:NumPixels)=0;
    amplitud(1,1:1600)=0;
PORT=ones(1,dim);
%  fase=fase;
%fase = fase.*0;
WriteFinisarRelative3(Dev,amplitud,fase,PORT)

%%
CloseFinisar3(Dev,0)
