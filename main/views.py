from django.shortcuts import render, redirect
from django.db import models
from django.http import HttpResponse
from django.contrib.auth.models import User, auth
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from .forms import SetForm, ModelForm
from .models import dataset, data, model, prediction
from django.db.models import Q
import pandas as pd
from sklearn import preprocessing
import tensorflow as tf
from json import dumps
from django.views.generic import View
from django.http import JsonResponse
# Create your views here.

def login(request):
    if request.method == 'POST':
        username = request.POST['uname']
        password = request.POST['psw']

        user = auth.authenticate(username = username, password =password)
        if user is not None:
            auth.login(request, user)
            return redirect('dash')
        
        else:
            messages.info(request,'invalid username or password')
            return redirect('/')
        
    else:
        if request.user.is_authenticated:
            return redirect('dash')
        else:
            return render(request, 'login.html')

def register(request):
    if request.method == 'POST':
        first_name = request.POST['fname']
        last_name = request.POST['lname']
        email = request.POST['email']
        user_name = request.POST['uname']
        password1 = request.POST['psw']
        if User.objects.filter(username = user_name).exists():
            messages.info(request,'Username taken')
            return redirect('register')
        elif User.objects.filter(email=email).exists():
            messages.info(request,'Email taken')
            return redirect('register')
        else:
            user = User.objects.create_user(username = user_name, password = password1, email = email, first_name= first_name, last_name = last_name)
            
            user.save()
            messages.info(request,'Account registered successfully')
            return redirect('login')
    else:
        return render(request, 'register.html')

def forgot(request):
    return render(request, 'forgot.html')

def dash(request):
    if request.user.is_authenticated:
        sets = dataset.objects.all().filter(user = request.user).values()
        sets2 =  model.objects.all().filter(Q(user = request.user) | Q(user_id = 1)).values()
        return render(request, 'dashboard.html',{
            'sets': sets,
            'sets2': sets2
        })
    else:
        return redirect('login')

def logout(request):
    auth.logout(request)
    messages.info(request,'You have successfully logged out')
    return redirect('/')

'''
def upload(request):
    context = {}
    if request.method =='POST':
        uploaded_file = request.FILES['document']
        fs = FileSystemStorage()
        name = fs.save(uploaded_file.name, uploaded_file)
        context['url'] = fs.url(name)
    return render(request, 'upload.html', context)


'''



##upload page that lets the user upload a new file



def upload_db(request):
    if request.user.is_authenticated:
        if request.method =='POST':
            f = request.FILES['Project Data'].temporary_file_path()
            try:
                df = pd.read_excel(f)
            except Exception:
                df = pd.read_csv(f)
            form = SetForm(request.POST)
            if form.is_valid():
                df = df.reset_index().groupby("ID", as_index=False).max()
                df['accepted'] = 0
                instance = form.save(commit=False)
                instance.user = request.user
                instance = form.save()
                
                df_records = df.to_dict('records')
                
                model_instances = [data(
                    name =record['ID'],
                    TCO =record['TCO'],
                    TVO =record['TVO'],
                    NET =record['NET'],
                    PP =record['PP'],
                    ROI =record['ROI'],
                    CapEx =record['CapEx'],
                    OneTime =record['OneTime'],
                    OnGoing =record['OnGoing'],
                    Revenue =record['Revenue'],
                    Saving =record['Saving'],
                    Avoid =record['Avoid'],
                    CostGrade =record['Cost Grade'],
                    ValueScore =record['Value Score'],
                    RiskScore =record['Risk Score'],
                    BlendedScore =record['Blended Score'],
                    CalcPriority =record['Calc Priority'],
                    OverridedPriority =record['Overrided Priority'],
                    dsid = instance,
                    accepted = record['accepted']
                    
                ) for record in df_records]
                data.objects.bulk_create(model_instances)

                count = data.objects.filter(dsid = instance).count()
                instance.size = count
                instance.save()


            
            return redirect('dash')
                

        else:
            form = SetForm()
            return render(request, 'upload_db.html',{'form': form})
    else:
        return redirect('login')


def test(request):
    return render(request, 'test.html')



##shows the list of files uploaded by that user

def set_list(request):
    if request.user.is_authenticated:
        sets = dataset.objects.all().filter(user = request.user).values()
        return render(request, 'set_list.html',{
            'sets': sets
        })
    else:
        return redirect('login')

def view(request):
    if request.user.is_authenticated:
        if request.method=="POST":



            return render(request, 'view_dataset.html')
        else:
            sets = data.objects.all().filter(dsid = request.GET['dataset']).values()
            df = pd.DataFrame(sets)
            df = df.fillna("")
            df['CalcPriority'] = ['Low' if x== 1.0 else 'Medium' if x == 2.0 else 'High' if x==3.0 else 'Critical' for x in df['CalcPriority']]
            df['OverridedPriority'] = ['Low' if x== 1 else 'Medium' if x == 2 else 'High' if x==3 else 'Critical' for x in df['OverridedPriority']]

            sets = df.to_dict('records')
            models = model.objects.all().filter(Q(user = request.user) | Q(user_id = 1)).values()
            instance = dataset.objects.get(id = request.GET['dataset'])
            print(instance.name)
            return render(request, 'view_dataset.html',{
                'sets':sets,
                'dataset' : request.GET['dataset'],
                'models' : models,
                'datasetname' : instance.name

            })
    else:
        return redirect('login')


def predict(request):
    if request.user.is_authenticated:
        if request.method == "POST":
            modelid = request.POST['model']
            dsetid = request.POST['dataset']
            datapoints = data.objects.all().filter(dsid = dsetid).values()
            if not prediction.objects.filter(mid = modelid, did = datapoints[0]['id']).exists():
                df = pd.DataFrame(datapoints)
                df1 = df.drop(df.columns[[0, 1, 2, 20]], axis = 1)
                df1 = df1.fillna(0)
                x = df1.values #returns a numpy array
                min_max_scaler = preprocessing.MinMaxScaler()
                x_scaled = min_max_scaler.fit_transform(x)
                m = model.objects.all().filter(id = modelid).values()
                m2 = model.objects.get(id = modelid)
                loadedmodel = tf.keras.models.load_model('media/'+m[0]['kfile'])
                pred = loadedmodel.predict(x_scaled)
                df['pred'] = pred
                df_records = df.to_dict('records')
                model_instances = [prediction(
                    did =data.objects.get(id = record['id']),
                    mid =m2,
                    score = record['pred'],
                    dsid = dataset.objects.get(id = dsetid)

                        
                ) for record in df_records]
                prediction.objects.bulk_create(model_instances)

            df = pd.DataFrame(datapoints)

            df2 =  pd.DataFrame(prediction.objects.all().filter(mid = modelid, dsid = dsetid).values())
            df['score'] = df2['score']
            df = df.fillna("")
            df['CalcPriority'] = ['Low' if x== 1.0 else 'Medium' if x == 2.0 else 'High' if x==3.0 else 'Critical' for x in df['CalcPriority']]
            df['OverridedPriority'] = ['Low' if x== 1 else 'Medium' if x == 2 else 'High' if x==3 else 'Critical' for x in df['OverridedPriority']]

            df = df.sort_values(by = ['score'], ascending = False)
            df_records1 = df.to_dict('records')
            models = model.objects.all().filter(Q(user = request.user) | Q(user_id = 1)).values()
            return render(request, 'view_dataset.html',{
                'sets':df_records1,
                'dataset' : dsetid,
                'models' : models

            })
        else:
            sets = dataset.objects.all().filter(user = request.user).values()
            return render(request, 'set_list.html',{
            'sets': sets
            })
    else:
        return redirect('login')


def models(request):
    if request.user.is_authenticated:
        sets = model.objects.all().filter(Q(user = request.user) | Q(user_id = 1)).values()
        return render(request, 'view_models.html',{
            'sets': sets
        })
    else:
        return redirect('login')

def modelcreate(request):
    if request.user.is_authenticated:
        if request.method =="POST":
            form = SetForm(request.POST)

            if form.is_valid():
                instance = form.save(commit=False)
                instance.user = request.user
                instance = form.save()

            return render(request, 'view_models.html')
        else:
            form = ModelForm()
            return render(request,'create_model.html',{'form': form})
    else:
        return redirect('login')

def delete_dataset(request):
    if request.user.is_authenticated:
        if request.method =='POST':
            dsid = request.POST['dsid']
            dataset.objects.filter(id = dsid).delete()

        return redirect('dash')
    else:
        return redirect('login')

def delete_data(request):
    if request.user.is_authenticated:
        if request.method =='POST':
            dsid = request.POST['dsid']
            dataid = request.POST['dataid']
            data.objects.filter(id = dataid).delete()
            instance = dataset.objects.get(id = dsid)
            count = data.objects.filter(dsid = instance).count()
            instance.size = count
            instance.save()
            sets = data.objects.all().filter(dsid = dsid).values()
            df = pd.DataFrame(sets)
            df = df.fillna("")
            sets = df.to_dict('records')
            return render(request, 'edit.html',{
                'sets':sets,
                'dataset' : dsid

            })
        return redirect('dash')
    else:
        return redirect('login')

def delete_model(request):
    if request.user.is_authenticated:
        if request.method =='POST':
            mid = request.POST['model']
            dataset.objects.filter(id = mid).delete()
        return redirect('dash')
    else:
        return redirect('login')

def edit(request):
    if request.user.is_authenticated:
        if request.method=="POST":
            return redirect('dash')
        else:
            id = request.GET['dsid']
            sets = data.objects.all().filter(dsid = id).values()
            df = pd.DataFrame(sets)
            df = df.fillna("")
            sets = df.to_dict('records')
            sets = dumps(sets)
            return render(request, 'edit.html',{
                'sets':sets,
                'dataset' : id

            })
    else:
        return redirect('login')


def edit_data(request):
    if request.user.is_authenticated:
        if request.method =='POST':
            dsid = request.POST['dsid']
            did = request.POST['dataid']
            instance = data.objects.filter(id = did)
            instance.name = request.POST['NAME']
            instance.TCO = request.POST['TCO']
            instance.TVO =request.POST['TVO']
            instance.NET =request.POST['NET']
            instance.PP =request.POST['PP']
            instance.ROI =request.POST['ROI']
            instance.CapEx =request.POST['CapEx']
            instance.OneTime =request.POST['OneTime']
            instance.OnGoing =request.POST['OnGoing']
            instance.Revenue =request.POST['Revenue']
            instance.Saving =request.POST['Saving']
            instance.Avoid =request.POST['Avoid']
            instance.CostGrade =request.POST['Cost Grade']
            instance.ValueScore =request.POST['Value Score']
            instance.RiskScore =request.POST['Risk Score']
            instance.BlendedScore =request.POST['Blended Score']
            instance.CalcPriority =request.POST['Calc Priority']
            instance.OverridedPriority =request.POST['Overrided Priority']
            instance.accepted = request.POST['accepted']
            instance.save()


            test = dataset.objects.get(id = dsid)
            test.save()
    else:
        return redirect('login')


def add_data(request):
    if request.user.is_authenticated:
        if request.method =='POST':
            dsid = request.POST['dsid']
            instance = data(dsid = dsid, 
            name = request.POST['NAME'],
            TCO = request.POST['TCO'],
            TVO =request.POST['TVO'],
            NET =request.POST['NET'],
            PP =request.POST['PP'],
            ROI =request.POST['ROI'],
            CapEx =request.POST['CapEx'],
            OneTime =request.POST['OneTime'],
            OnGoing =request.POST['OnGoing'],
            Revenue =request.POST['Revenue'],
            Saving =request.POST['Saving'],
            Avoid =request.POST['Avoid'],
            CostGrade =request.POST['Cost Grade'],
            ValueScore =request.POST['Value Score'],
            RiskScore =request.POST['Risk Score'],
            BlendedScore =request.POST['Blended Score'],
            CalcPriority =request.POST['Calc Priority'],
            OverridedPriority =request.POST['Overrided Priority'],
            accepted = request.POST['accepted'])
    else:
        return redirect('login')



        
def data_update( request):
    id = request.POST.get('row_id')
    print(id)
    x = request.POST.get('col_name')
    print(x)            
    instance = data.objects.get(id = id)
    arr = request.POST.get('arr')
    print(arr)
    instance.x = arr[x]
    print(instance.x)
    instance.save()
    return JsonResponse({'data': 'worked'}, status =200)

def edit_single_data(request):
        dataid = request.POST.get('row_id')
        datacolumn = list(request.POST.keys())[0]
        datavalue = request.POST.get(datacolumn)
        instance = data.objects.get(id = dataid)
        instance.datacolumn = datavalue
        instance.save()

        print(dataid, datacolumn, datavalue,instance.datacolumn, instance.TCO)
        return JsonResponse({'status': True}, status = 200)



def edit_whole_data(request):
        arr= (request.POST.get('content'))
        print(arr)
        return JsonResponse({'status': True}, status = 200)
        