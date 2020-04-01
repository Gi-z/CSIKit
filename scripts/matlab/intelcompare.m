invalid = false;

for t=1:size(csi)
   test = csi{t}.csi == csi_trace{t}.csi;
   if all(test(:)==1)
       continue;
   else
       disp(t);
       invalid = true;
   end
end

if invalid == false
    disp("success.");
else
    disp("failure.");
end