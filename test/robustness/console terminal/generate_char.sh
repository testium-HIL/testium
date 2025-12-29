chars='<=>| -,;:!/."()[]{}*\&#%+012345689abcdefghiklmnopqrstuvwxyzABCD'
for j in {1..256} ;
do
    for i in {1..256} ; do
        echo -n "${chars:RANDOM%${#chars}:1}"
    done
    echo
    sleep 0.01
done